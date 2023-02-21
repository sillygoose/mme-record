import logging
import time
import datetime

from state_engine import delete_state, get_state_value, set_state, odometer_km, odometer_miles, speed_kph, speed_mph
from state_engine import delete_state
from state_engine import get_InferredKey, get_GearCommanded
from state_engine import get_EngineStartRemote, get_EngineStartDisable

from did import InferredKey, GearCommanded
from did import EngineStartRemote, EngineStartDisable

from vehicle_state import VehicleState, CallType
from hash import *

from influxdb import influxdb_trip
from geocoding import reverse_geocode
from logfiles import rollover


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
            delete_state(Hash.HvbEnergyGained, True)
            delete_state(Hash.HvbEnergyLost, True)
            delete_state(Hash.GpsElevationMax, True)
            delete_state(Hash.GpsElevationMin, True)
            delete_state(Hash.HiresSpeedMax, True)
            delete_state(Hash.HvbPowerMax, True)
            delete_state(Hash.HvbPowerMin, True)
            delete_state(Hash.ExtTemperatureSum, True)
            delete_state(Hash.ExtTemperatureCount, True)
            delete_state(Hash.ExteriorTemperature, True)

        elif call_type == CallType.Outgoing:
            for hash in Trip._requiredHashes:
                assert get_state_value(hash, None) is not None, f"{hash.name}"
            odometer = get_state_value(Hash.HiresOdometer)
            _LOGGER.info(f"Starting new trip in {get_state_value(Hash.VehicleID)}, odometer: {odometer_km(odometer):.01f} km ({odometer_miles(odometer):.01f} mi)")

        elif call_type == CallType.Default:
            for hash in Trip._requiredHashes:
                if (hash_value := get_state_value(hash, None)) is None:
                    arbitration_id, did_id, _ = get_hash_fields(hash)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: Waiting for required DID: '{hash.name}'")
                    return new_state
                self._trip_log[hash] = hash_value

            if gear_commanded := get_GearCommanded('trip_starting'):
                if gear_commanded != GearCommanded.Park:
                    new_state = VehicleState.Trip
                else:
                    self._trip_log = None
                    new_state = VehicleState.On
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
        if call_type == CallType.Incoming:
            return new_state

        if call_type == CallType.Default:
            if not self.command_queue_empty():
                return new_state

            if inferred_key := get_InferredKey('trip_ending'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote('trip_ending'):
                        new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_disable := get_EngineStartDisable('trip_ending'):
                        new_state = VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory

        elif call_type == CallType.Outgoing:
            trip = self._trip_log
            starting_time = set_state(Hash.TR_TimeStart, trip.get('time'))
            ending_time = set_state(Hash.TR_TimeEnd, int(time.time()))
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
            ending_soh = set_state(Hash.TR_SohEnd, get_state_value(Hash.HvbSoH))
            energy_gained = set_state(Hash.TR_EnergyGained, get_state_value(Hash.HvbEnergyGained))
            energy_lost = set_state(Hash.TR_EnergyLost, get_state_value(Hash.HvbEnergyLost))
            hvb_power_min = set_state(Hash.TR_HvbPowerMin, get_state_value(Hash.HvbPowerMin))
            hvb_power_max = set_state(Hash.TR_HvbPowerMax, get_state_value(Hash.HvbPowerMax))

            trip_distance = set_state(Hash.TR_Distance, odometer_km(ending_odometer - starting_odometer))
            elevation_change = set_state(Hash.TR_ElevationChange, get_state_value(Hash.GpsElevation) - trip.get(Hash.GpsElevation))
            max_elevation = set_state(Hash.TR_MaxElevation, get_state_value(Hash.GpsElevationMax))
            min_elevation = set_state(Hash.TR_MinElevation, get_state_value(Hash.GpsElevationMin))
            max_speed = set_state(Hash.TR_MaxSpeed, speed_kph(get_state_value(Hash.HiresSpeedMax)))
            average_speed = set_state(Hash.TR_AverageSpeed, ((trip_distance / duration_seconds) * 3600) if duration_seconds > 0 else 0.0)
            wh_used = set_state(Hash.TR_EnergyUsed, (trip.get(Hash.HvbEtE) - get_state_value(Hash.HvbEtE)))
            calculated_wh_used = get_state_value(Hash.HvbEnergy) - trip.get(Hash.HvbEnergy)
            efficiency_km_kwh = set_state(Hash.TR_EnergyEfficiency, 0.0 if wh_used == 0.0 else trip_distance / (wh_used * 0.001))
            efficiency_miles_kwh = efficiency_km_kwh * 0.6213712
            average_temperature = set_state(Hash.TR_ExteriorAverage, get_state_value(Hash.ExtTemperatureSum) / get_state_value(Hash.ExtTemperatureCount))

            _LOGGER.info(f"Trip in {get_state_value(Hash.VehicleID)} started at {starting_datetime} and lasted for {hours} hours, {minutes} minutes, {seconds} seconds")
            _LOGGER.info(f"        starting odometer: {odometer_km(starting_odometer):.01f} km ({odometer_miles(starting_odometer):.01f} mi)")
            _LOGGER.info(f"        starting elevation: {starting_elevation} m")
            _LOGGER.info(f"        starting SoC: {starting_socd:.01f}%, starting EtE: {starting_ete} Wh")
            _LOGGER.info(f"        starting temperature: {starting_temperature}°C")
            _LOGGER.info(f"ending at {ending_datetime}")
            _LOGGER.info(f"        ending odometer: {odometer_km(ending_odometer):.1f} km ({odometer_miles(ending_odometer):.1f} mi)")
            _LOGGER.info(f"        distance covered: {odometer_km(trip_distance):.1f} km ({odometer_miles(trip_distance):.1f} mi)")
            _LOGGER.info(f"        ending elevation {ending_elevation:.0f} m, elevation change {elevation_change:.0f} m")
            _LOGGER.info(f"        minimum elevation: {min_elevation:.1f} m, maximum elevation: {max_elevation:.1f} m")
            _LOGGER.info(f"        ending SoC: {ending_socd:.1f}%, ending EtE: {ending_ete} Wh, ΔEtE: {wh_used} Wh, calculated ΔEtE: {calculated_wh_used} Wh")
            _LOGGER.info(f"        maximum power: {hvb_power_max} W, minimum power seen: {hvb_power_min} W")
            _LOGGER.info(f"        energy gained: {energy_gained} Wh, energy lost: {energy_lost} Wh")
            _LOGGER.info(f"        energy efficiency: {efficiency_km_kwh:.2f} km/kWh ({efficiency_miles_kwh:.2f} mi/kWh)")
            _LOGGER.info(f"        maximum speed: {max_speed:.1f} kph ({speed_mph(max_speed):.1f} mph)")
            _LOGGER.info(f"        average speed: {average_speed:.1f} kph ({speed_mph(average_speed):.1f} mph)")
            _LOGGER.info(f"        ending temperature: {ending_temperature}°C")
            _LOGGER.info(f"        average temperature: {average_temperature}°C")

            if trip_distance >= self._minimum_trip:
                _LOGGER.info(f"        trip timestamps: {get_state_value(Hash.TR_TimeStart)}   {get_state_value(Hash.TR_TimeEnd)}")
                tags = [Hash.Vehicle]
                fields = [
                        Hash.TR_TimeStart, Hash.TR_TimeEnd,
                        Hash.TR_OdometerStart, Hash.TR_OdometerEnd, Hash.TR_Distance,
                        Hash.TR_LatitudeStart, Hash.TR_LatitudeEnd, Hash.TR_LongitudeStart, Hash.TR_LongitudeEnd, Hash.TR_ElevationStart, Hash.TR_ElevationEnd,
                        Hash.TR_MaxElevation, Hash.TR_MinElevation, Hash.TR_ElevationChange,
                        Hash.TR_SocDStart, Hash.TR_SocDEnd, Hash.TR_EtEStart, Hash.TR_EtEEnd, Hash.TR_SohEnd,
                        Hash.TR_HvbPowerMin, Hash.TR_HvbPowerMax,
                        Hash.TR_EnergyGained, Hash.TR_EnergyLost, Hash.TR_EnergyUsed, Hash.TR_EnergyEfficiency,
                        Hash.TR_MaxSpeed, Hash.TR_AverageSpeed,
                        Hash.TR_ExteriorStart, Hash.TR_ExteriorEnd, Hash.TR_ExteriorAverage,
                    ]
                influxdb_trip(tags=tags, fields=fields, trip_start=Hash.TR_TimeStart)
                filename = 'trip_' + datetime.datetime.fromtimestamp(starting_time).strftime('%Y-%m-%d_%H_%M')
                self._file_manager.flush(filename)
                rollover(filename)
            self._trip_log = None

        return new_state
