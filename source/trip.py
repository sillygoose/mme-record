import logging
import time
import datetime

from typing import List

from state_engine import get_state_value, set_state
from state_engine import get_InferredKey, get_GearCommanded
from state_engine import get_EngineStartRemote, get_EngineStartDisable

from did import InferredKey, GearCommanded
from did import EngineStartRemote, EngineStartDisable

from vehicle_state import VehicleState, CallType
from hash import *

from influxdb import influxdb_record_trip
from geocoding import reverse_geocode


_LOGGER = logging.getLogger('mme')


class Trip:

    def __init__(self) -> None:
        self._trip_log = None

    def trip_starting(self, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Incoming:
            assert self._trip_log is None
            self._trip_log = {
                'time': int(time.time()),
            }
            set_state(Hash.HvbEnergyGained, 0)
            set_state(Hash.HvbEnergyLost, 0)
            set_state(Hash.HiresSpeedMax, 0)

        elif call_type == CallType.Outgoing:
            requiredStates = [Hash.HiresOdometer, Hash.HvbSoCD, Hash.HvbEtE, Hash.GpsLatitude, Hash.GpsLongitude, Hash.GpsElevation, Hash.ExteriorTemperature]
            for state in requiredStates:
                assert get_state_value(state, None) is not None

        elif call_type == CallType.Default:
            requiredStates = [Hash.HiresOdometer, Hash.HvbSoCD, Hash.HvbEtE, Hash.GpsLatitude, Hash.GpsLongitude, Hash.GpsElevation, Hash.ExteriorTemperature]
            ready_to_continue = True
            for state in requiredStates:
                if (state_value := get_state_value(state, None)) is None:
                    return new_state
                    #ready_to_continue = False
                    #break
                else:
                    self._trip_log[state] = state_value
            if ready_to_continue:
                if gear_commanded := get_GearCommanded(Hash.GearCommanded, 'trip_starting'):
                    if gear_commanded != GearCommanded.Park:
                        new_state = VehicleState.Trip
                    else:
                        self._trip_log = None
                        new_state = VehicleState.Idle
        return new_state

    def trip_ending(self, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Outgoing:
            pass
        elif call_type == CallType.Default:
            if inferred_key := get_InferredKey(Hash.InferredKey, 'trip_ending'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'trip_ending'):
                        new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_disable := get_EngineStartDisable(Hash.EngineStartDisable, 'trip_ending'):
                        new_state = VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory
        elif call_type == CallType.Incoming:
            starting_time = self._trip_log.get('time')
            ending_time = int(time.time())
            duration_seconds = ending_time - starting_time

            trip = self._trip_log
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
                'exterior_t':           {'starting': trip.get(Hash.ExteriorTemperature), 'ending': get_state_value(Hash.ExteriorTemperature)},
            }
            _LOGGER.info(f"Trip started at {starting_datetime} and lasted for {hours} hours, {minutes} minutes")
            _LOGGER.info(f"        odometer {trip.get(Hash.HiresOdometer):.01f} km")
            _LOGGER.info(f"        {reverse_geocode(trip.get(Hash.GpsLatitude), trip.get(Hash.GpsLongitude))}")
            _LOGGER.info(f"        elevation {trip.get(Hash.GpsElevation):.01f} m")
            _LOGGER.info(f"        SoC {trip.get(Hash.HvbSoCD)}%, EtE { trip.get(Hash.HvbEtE)} Wh")
            _LOGGER.info(f"        temperature {trip.get(Hash.ExteriorTemperature)}°")
            _LOGGER.info(f"ending at {ending_datetime}")
            _LOGGER.info(f"        odometer {get_state_value(Hash.HiresOdometer):.01f} km, distance covered {trip_distance:.01f}")
            _LOGGER.info(f"        {reverse_geocode(get_state_value(Hash.GpsLatitude), get_state_value(Hash.GpsLongitude))}")
            _LOGGER.info(f"        elevation {get_state_value(Hash.GpsElevation):.01f} m, elevation change {elevation_change:.01f} m")
            _LOGGER.info(f"        SoC {get_state_value(Hash.HvbSoCD)}%, EtE {get_state_value(Hash.HvbEtE)} Wh")
            _LOGGER.info(f"        energy gained {get_state_value(Hash.HvbEnergyGained):.0f} Wh, energy lost {get_state_value(Hash.HvbEnergyLost):.0f} Wh")
            _LOGGER.info(f"        maximum speed {get_state_value(Hash.HiresSpeedMax):.01f} kph")
            _LOGGER.info(f"        temperature {get_state_value(Hash.ExteriorTemperature)}°")
            influxdb_record_trip(details=trip_details, vehicle=self._vehicle_name)
            self._trip_log = None

        return new_state

    def trip(self, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if gear_commanded := get_GearCommanded(Hash.GearCommanded, 'trip'):
                if gear_commanded == GearCommanded.Park:
                    new_state = VehicleState.Trip_Ending
        return new_state
