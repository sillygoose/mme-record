import logging
import time
import datetime

from typing import List
from config.configuration import Configuration

from state_engine import get_state_value, set_state
from state_engine import get_InferredKey, get_GearCommanded
from state_engine import get_EngineStartRemote, get_EngineStartDisable
from state_engine import delete_did_cache

from did import InferredKey, GearCommanded
from did import EngineStartRemote, EngineStartDisable

from vehicle_state import VehicleState, CallType
from hash import *

from influxdb import influxdb_record_trip
from geocodio import GeocodioClient


_LOGGER = logging.getLogger('mme')


class Trip:

    def __init__(self, config: Configuration) -> None:
        self._trip_log = None
        self._geocodio_client = None
        geocodio = dict(config.geocodio)
        if geocodio.get('enable', False):
            self._geocodio_client = GeocodioClient(geocodio.get('api_key'))

    def trip_starting(self, state_keys: List, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Incoming:
            assert self._trip_log is None
            self._trip_log = {
                'time': int(time.time()),
            }
            set_state(Hash.HvbEnergyGained, 0)
            set_state(Hash.HvbEnergyLost, 0)
            set_state(Hash.HiresSpeedMax, 0)
            delete_did_cache('07E2:1E12')

        elif call_type == CallType.Outgoing:
            assert get_state_value(Hash.HiresOdometer, None) is not None
            assert get_state_value(Hash.HvbSoC, None) is not None
            assert get_state_value(Hash.HvbSoCD, None) is not None
            assert get_state_value(Hash.HvbEtE, None) is not None
            assert get_state_value(Hash.GpsLatitude, None) is not None
            assert get_state_value(Hash.GpsLongitude, None) is not None
            assert get_state_value(Hash.GpsElevation, None) is not None
            assert get_state_value(Hash.InteriorTemperature, None) is not None
            assert get_state_value(Hash.ExteriorTemperature, None) is not None
        elif call_type == CallType.Default:
            if self._trip_log.get(Hash.HiresOdometer) is None:
                if (hires_odometer := get_state_value(Hash.HiresOdometer, None)) is not None:
                    self._trip_log[Hash.HiresOdometer] = hires_odometer
                    _LOGGER.debug(f"Saved hires_odometer initial value: {hires_odometer:.01f}")
            if self._trip_log.get(Hash.HvbSoCD) is None:
                if (soc_displayed := get_state_value(Hash.HvbSoCD, None)) is not None:
                    self._trip_log[Hash.HvbSoCD] = soc_displayed
                    _LOGGER.debug(f"Saved socd initial value: {soc_displayed:.01f}")
            if self._trip_log.get(Hash.HvbEtE) is None:
                if (hvb_ete := get_state_value(Hash.HvbEtE, None)) is not None:
                    self._trip_log[Hash.HvbEtE] = hvb_ete
                    _LOGGER.debug(f"Saved hvb_ete initial value: {hvb_ete:.0f}")
            if self._trip_log.get(Hash.GpsLatitude) is None:
                if (latitude := get_state_value(Hash.GpsLatitude, None)) is not None:
                    self._trip_log[Hash.GpsLatitude] = latitude
                    _LOGGER.debug(f"Saved latitude initial value: {latitude:.05f}")
            if self._trip_log.get(Hash.GpsLongitude) is None:
                if (longitude := get_state_value(Hash.GpsLongitude, None)) is not None:
                    self._trip_log[Hash.GpsLongitude] = longitude
                    _LOGGER.debug(f"Saved longitude initial value: {longitude:.05f}")
            if self._trip_log.get(Hash.GpsElevation) is None:
                if (elevation := get_state_value(Hash.GpsElevation, None)) is not None:
                    self._trip_log[Hash.GpsElevation] = elevation
                    _LOGGER.debug(f"Saved elevation initial value: {elevation:.01f}")
            if self._trip_log.get(Hash.ExteriorTemperature) is None:
                if (exterior_temperature := get_state_value(Hash.ExteriorTemperature, None)) is not None:
                    self._trip_log[Hash.ExteriorTemperature] = exterior_temperature
                    _LOGGER.debug(f"Saved exterior temperature value: {exterior_temperature:.0f}")

            for key in state_keys:
                _LOGGER.debug(f"testing: {key}")
                if gear_commanded := get_GearCommanded(key, 'trip_starting'):
                    if gear_commanded != GearCommanded.Park:
                        _LOGGER.debug(f"not park:")
                        new_state = VehicleState.Trip
                    else:
                        _LOGGER.debug(f"park:")
                        new_state = VehicleState.On
                        self._trip_log = None
        return new_state

    def trip_ending(self, state_keys: List, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Outgoing:
            #_LOGGER.debug(f"CallType: {call_type.name}")
            pass
        elif call_type == CallType.Default:
            _LOGGER.debug(f"CallType: {call_type.name}")
            for key in state_keys:
                if gear_commanded := get_GearCommanded(key, 'trip_ending'):
                    if gear_commanded != GearCommanded.Park:
                        _LOGGER.debug(f"Nooooooo!")
                        new_state = VehicleState.Trip
                elif inferred_key := get_InferredKey(key, 'trip_ending'):
                        if inferred_key == InferredKey.KeyOut:
                            if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'trip_ending'):
                                new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                        elif inferred_key == InferredKey.KeyIn:
                            if engine_start_disable := get_EngineStartDisable(Hash.EngineStartDisable, 'trip_ending'):
                                new_state = VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory
        elif call_type == CallType.Incoming:
            #_LOGGER.debug(f"CallType: {call_type.name}")
            starting_time = self._trip_log.get('time')
            ending_time = int(time.time())
            duration_seconds = ending_time - starting_time

            trip = self._trip_log
            ###
            starting_odometer = trip.get(Hash.HiresOdometer)
            starting_socd = trip.get(Hash.HvbSoCD)
            starting_ete = trip.get(Hash.HvbEtE)
            starting_latitude = trip.get(Hash.GpsLatitude)
            starting_longitude = trip.get(Hash.GpsLongitude)
            starting_elevation = trip.get(Hash.GpsElevation)
            starting_exterior_temperature = trip.get(Hash.ExteriorTemperature)
            ###

            starting_datetime = datetime.datetime.fromtimestamp(starting_time).strftime('%Y-%m-%d %H:%M')
            ending_datetime = datetime.datetime.fromtimestamp(ending_time).strftime('%Y-%m-%d %H:%M')
            hours, rem = divmod(duration_seconds, 3600)
            minutes, _ = divmod(rem, 60)
            trip_distance = get_state_value(Hash.HiresOdometer) - trip.get(Hash.HiresOdometer)
            elevation_change = get_state_value(Hash.GpsElevation) - trip.get(Hash.GpsElevation)

            trip_details = {
                'time':                 starting_time,
                'duration':             duration_seconds,
                'odometer':             {'starting': trip.get(Hash.HiresOdometer), 'ending': get_state_value(Hash.HiresOdometer)},
                'socd':                 {'starting': trip.get(Hash.HvbSoCD), 'ending': get_state_value(Hash.HvbSoCD)},
                'ete':                  {'starting': trip.get(Hash.HvbEtE), 'ending': get_state_value(Hash.HvbEtE)},
                'latitude':             {'starting': trip.get(Hash.GpsLatitude), 'ending': get_state_value(Hash.GpsLatitude)},
                'longitude':            {'starting': trip.get(Hash.GpsLongitude), 'ending': get_state_value(Hash.GpsLongitude)},
                'elevation':            {'starting': trip.get(Hash.GpsElevation), 'ending': get_state_value(Hash.GpsElevation)},
                'temperature':          {'starting': trip.get(Hash.ExteriorTemperature), 'ending': get_state_value(Hash.ExteriorTemperature)},
            }
            _LOGGER.info(f"Trip started at {starting_datetime} and lasted for {hours} hours, {minutes} minutes")
            _LOGGER.info(f"        odometer {starting_odometer:.01f} km")
            if self._geocodio_client is None:
                _LOGGER.info(f"        location ({starting_latitude:.06f},{starting_longitude:.06f})")
            else:
                start_address = self._geocodio_client.reverse((starting_latitude, starting_longitude))
                _LOGGER.info(f"        {start_address.formatted_address}")
            _LOGGER.info(f"        elevation {starting_elevation:.01f} m")
            _LOGGER.info(f"        SoC {starting_socd}%, EtE {starting_ete} Wh")
            _LOGGER.info(f"        temperature {starting_exterior_temperature}°")
            _LOGGER.info(f"ending at {ending_datetime}")
            _LOGGER.info(f"        odometer {get_state_value(Hash.HiresOdometer):.01f} km, distance covered {trip_distance:.01f}")
            if self._geocodio_client is None:
                _LOGGER.info(f"        location ({get_state_value(Hash.GpsLatitude):.06f},{get_state_value(Hash.GpsLongitude):.06f})")
            else:
                end_address = self._geocodio_client.reverse((get_state_value(Hash.GpsLatitude), get_state_value(Hash.GpsLongitude)))
                _LOGGER.info(f"        {end_address.formatted_address}")
            _LOGGER.info(f"        elevation {get_state_value(Hash.GpsElevation):.01f} m, elevation change {elevation_change:.01f} m")
            _LOGGER.info(f"        SoC {get_state_value(Hash.HvbSoCD)}%, EtE {get_state_value(Hash.HvbEtE)} Wh")
            _LOGGER.info(f"        energy gained {get_state_value(Hash.HvbEnergyGained):.0f} Wh, energy lost {get_state_value(Hash.HvbEnergyLost):.0f} Wh")
            _LOGGER.info(f"        maximum speed {get_state_value(Hash.HiresSpeedMax):.01f} kph")
            _LOGGER.info(f"        temperature {get_state_value(Hash.ExteriorTemperature)}°")
            influxdb_record_trip(details=trip_details, vehicle=self._vehicle_name)
            self._trip_log = None

        return new_state

    def trip(self, state_keys: List, call_type: CallType = CallType.Default) -> VehicleState:
        #_LOGGER.debug(f"CallType: {call_type.name}")
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            for key in state_keys:
                if gear_commanded := get_GearCommanded(key, 'trip'):
                    if gear_commanded == GearCommanded.Park:
                        new_state = VehicleState.Trip_Ending
        return new_state
