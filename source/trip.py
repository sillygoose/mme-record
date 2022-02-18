import logging
import time
import datetime

from state_engine import get_state_value, set_state, odometer_km, odometer_miles, socd, speed_kph, speed_mph
from state_engine import get_InferredKey, get_GearCommanded
from state_engine import get_EngineStartRemote, get_EngineStartDisable

from did import InferredKey, GearCommanded
from did import EngineStartRemote, EngineStartDisable

from vehicle_state import VehicleState, CallType
from hash import *

from influxdb import influxdb_trip
from geocoding import reverse_geocode


_LOGGER = logging.getLogger('mme')


class Trip:

    def __init__(self) -> None:
        self._trip_log = None

    _requiredHashes = [
            Hash.HiresOdometer, Hash.HvbSoCD, Hash.HvbEtE, Hash.HvbEnergy, Hash.ExteriorTemperature,
            Hash.GpsLatitude, Hash.GpsLongitude, Hash.GpsElevation,
        ]

    def trip_starting(self, call_type: CallType) -> VehicleState:
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
            for hash in Trip._requiredHashes:
                assert get_state_value(hash, None) is not None, f"{hash.name}"
            odometer = get_state_value(Hash.HiresOdometer)
            _LOGGER.info(f"Starting new trip, odometer: {odometer_km(odometer):.01f} km ({odometer_miles(odometer):.01f} mi)")

        elif call_type == CallType.Default:
            for hash in Trip._requiredHashes:
                if (hash_value := get_state_value(hash, None)) is None:
                    arbitration_id, did_id, _ = get_hash_fields(hash)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: Missing required DID: '{hash.name}'")
                    return new_state
                self._trip_log[hash] = hash_value

            if gear_commanded := get_GearCommanded('trip_starting'):
                if gear_commanded != GearCommanded.Park:
                    new_state = VehicleState.Trip
                else:
                    self._trip_log = None
                    new_state = VehicleState.Idle
        return new_state


    def trip(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if gear_commanded := get_GearCommanded('trip'):
                if gear_commanded == GearCommanded.Park:
                    new_state = VehicleState.Trip_Ending
        return new_state


    def trip_ending(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Outgoing:
            pass
        elif call_type == CallType.Default:
            if inferred_key := get_InferredKey('trip_ending'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote('trip_ending'):
                        new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_disable := get_EngineStartDisable('trip_ending'):
                        new_state = VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory
        elif call_type == CallType.Incoming:
            trip = self._trip_log
            vehicle = set_state(Hash.Vehicle, self._vehicle_name)
            starting_time = set_state(Hash.TR_StartTime, trip.get('time'))
            ending_time = set_state(Hash.TR_EndTime, int(time.time()))
            starting_datetime = datetime.datetime.fromtimestamp(starting_time).strftime('%Y-%m-%d %H:%M')
            ending_datetime = datetime.datetime.fromtimestamp(ending_time).strftime('%Y-%m-%d %H:%M')
            duration_seconds = ending_time - starting_time
            hours, rem = divmod(duration_seconds, 3600)
            minutes, seconds = divmod(rem, 60)

            starting_odometer = set_state(Hash.TR_OdometerStart, trip.get(Hash.HiresOdometer))
            starting_latitude = set_state(Hash.TR_LatitudeStart, trip.get(Hash.GpsLatitude))
            starting_longitude = set_state(Hash.TR_LongitudeStart, trip.get(Hash.GpsLongitude))
            starting_elevation = set_state(Hash.TR_ElevationStart, trip.get(Hash.GpsElevation))
            starting_temperature = set_state(Hash.TR_ExteriorStart, trip.get(Hash.ExteriorTemperature))
            starting_socd = set_state(Hash.TR_SocDStart, trip.get(Hash.HvbSoCD))
            starting_ete = set_state(Hash.TR_EtEStart, trip.get(Hash.HvbEtE))

            ending_odometer = set_state(Hash.TR_OdometerEnd, get_state_value(Hash.HiresOdometer))
            ending_latitude = set_state(Hash.TR_LatitudeEnd, get_state_value(Hash.GpsLatitude))
            ending_longitude = set_state(Hash.TR_LongitudeEnd, get_state_value(Hash.GpsLongitude))
            ending_elevation = set_state(Hash.TR_ElevationEnd, get_state_value(Hash.GpsElevation))
            ending_temperature = set_state(Hash.TR_ExteriorEnd, get_state_value(Hash.ExteriorTemperature))
            ending_socd = set_state(Hash.TR_SocDEnd, get_state_value(Hash.HvbSoCD))
            ending_ete = set_state(Hash.TR_EtEEnd, get_state_value(Hash.HvbEtE))
            energy_gained = set_state(Hash.TR_EnergyGained, int(get_state_value(Hash.HvbEnergyGained)))
            energy_lost = set_state(Hash.TR_EnergyLost, int(get_state_value(Hash.HvbEnergyLost)))

            trip_distance = set_state(Hash.TR_Distance, get_state_value(Hash.HiresOdometer) - trip.get(Hash.HiresOdometer))
            elevation_change = set_state(Hash.TR_ElevationChange, get_state_value(Hash.GpsElevation) - trip.get(Hash.GpsElevation))
            max_elevation = set_state(Hash.TR_MaxElevation, get_state_value(Hash.GpsElevationMax))
            min_elevation = set_state(Hash.TR_MinElevation, get_state_value(Hash.GpsElevationMin))
            max_speed = set_state(Hash.TR_MaxSpeed, speed_kph(get_state_value(Hash.HiresSpeedMax)))
            wh_used = set_state(Hash.TR_EnergyUsed, (trip.get(Hash.HvbEtE) - get_state_value(Hash.HvbEtE)))
            calculated_wh_used = get_state_value(Hash.HvbEnergy) - trip.get(Hash.HvbEnergy)
            efficiency_km_kwh = 0.0 if wh_used == 0.0 else trip_distance / (wh_used * 0.001)
            efficiency_miles_kwh = efficiency_km_kwh * 0.6213712

            _LOGGER.info(f"Trip in '{vehicle}' started at {starting_datetime} and lasted for {hours} hours, {minutes} minutes, {seconds} seconds")
            _LOGGER.info(f"        starting odometer: {odometer_km(starting_odometer):.01f} km ({odometer_miles(starting_odometer):.01f} mi)")
            _LOGGER.info(f"        starting point: {reverse_geocode(starting_latitude, starting_longitude)}")
            _LOGGER.info(f"        starting elevation: {starting_elevation:.01f} m")
            _LOGGER.info(f"        starting SoC: {socd(starting_socd)}%, starting EtE: {starting_ete} Wh")
            _LOGGER.info(f"        starting temperature: {starting_temperature}°C")
            _LOGGER.info(f"ending at {ending_datetime}")
            _LOGGER.info(f"        ending odometer: {odometer_km(ending_odometer):.01f} km ({odometer_miles(ending_odometer):.01f} mi)")
            _LOGGER.info(f"        ending point: {reverse_geocode(ending_latitude, ending_longitude)}")
            _LOGGER.info(f"        distance covered: {odometer_km(trip_distance):.01f} km ({odometer_miles(trip_distance):.01f} mi)")
            _LOGGER.info(f"        ending elevation {ending_elevation:.01f} m, elevation change {elevation_change:.01f} m")
            _LOGGER.info(f"        minimum elevation seen: {min_elevation:.01f} m, maximum elevation seen {max_elevation:.01f} m")
            _LOGGER.info(f"        ending SoC: {socd(ending_socd)}%, ending EtE: {ending_ete} Wh, ΔEtE: {wh_used} Wh, calculated ΔEtE: {int(calculated_wh_used)} Wh")
            _LOGGER.info(f"        maximum power seen: {get_state_value(Hash.HvbPowerMax)} W, minimum power seen: {get_state_value(Hash.HvbPowerMin)} W")
            _LOGGER.info(f"        energy gained: {energy_gained} Wh, energy lost: {energy_lost} Wh")
            _LOGGER.info(f"        energy efficiency: {efficiency_km_kwh:.02f} km/kWh ({efficiency_miles_kwh:.02f} mi/kWh)")
            _LOGGER.info(f"        maximum speed seen: {max_speed:.01f} kph ({speed_mph(max_speed):.01f} mph)")
            _LOGGER.info(f"        ending temperature: {ending_temperature}°C")

            tags = [Hash.Vehicle]
            fields = [
                    Hash.TR_OdometerStart, Hash.TR_OdometerEnd,
                    Hash.TR_Distance, Hash.TR_ElevationChange,
                    Hash.TR_LatitudeStart, Hash.TR_LatitudeEnd, Hash.TR_LongitudeStart, Hash.TR_LongitudeEnd, Hash.TR_ElevationStart, Hash.TR_ElevationEnd,
                    Hash.TR_SocDStart, Hash.TR_SocDEnd, Hash.TR_EtEStart, Hash.TR_EtEEnd, Hash.TR_EnergyGained, Hash.TR_EnergyLost, Hash.TR_EnergyUsed,
                    Hash.TR_ExteriorStart, Hash.TR_ExteriorEnd,
                    Hash.TR_MaxElevation, Hash.TR_MinElevation, Hash.TR_MaxSpeed,
                ]
            influxdb_trip(tags=tags, fields=fields, trip_start=Hash.TR_StartTime)
            self._trip_log = None

        return new_state
