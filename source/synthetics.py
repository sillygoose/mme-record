import logging
from time import time_ns

from typing import List

from state_engine import get_state, get_state_value, set_state, set_state_interval
from hash import get_hash_fields
from hash import *


_LOGGER = logging.getLogger('mme')

class Synthetics:

    _synthetic_hashes = {
        Hash.HvbVoltage:                Hash.HvbPower,
        Hash.HvbCurrent:                Hash.HvbPower,
        Hash.LvbVoltage:                Hash.LvbPower,
        Hash.LvbCurrent:                Hash.LvbPower,
        Hash.ChargerInputVoltage:       Hash.ChargerInputPower,
        Hash.ChargerInputCurrent:       Hash.ChargerInputPower,
        Hash.ChargerOutputVoltage:      Hash.ChargerOutputPower,
        Hash.ChargerOutputCurrent:      Hash.ChargerOutputPower,
        Hash.HiresSpeed:                Hash.HiresSpeedMax,
        Hash.GpsElevation:              Hash.GpsElevationMin,
        Hash.ExteriorTemperature:       Hash.ExtTemperatureSum,
        Hash.HiresOdometer:             Hash.WhPerKilometer,
        Hash.GpsLatitude:               Hash.WhPerGpsSegment,
    }


def update_synthetics(hash: Hash) -> List[dict]:
    synthetics = []
    try:
        if synthetic_hash := Synthetics._synthetic_hashes.get(Hash(hash), None):
            if synthetic_hash == Hash.HvbPower:
                hvb_power_interval_start, interval_start = get_state(Hash.HvbPower, 0.0)

                hvb_power = int(get_state_value(Hash.HvbVoltage, 0.0) * get_state_value(Hash.HvbCurrent, 0.0))
                interval_end = set_state_interval(Hash.HvbPower, hvb_power)
                arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.HvbPower)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': hvb_power})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: HVB power: {hvb_power} W (calculated)")

                if hvb_power > get_state_value(Hash.HvbPowerMax, -9999999.0):
                    set_state(Hash.HvbPowerMax, hvb_power)
                    arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.HvbPowerMax)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: Maximum HVB power seen: {hvb_power} W (calculated)")
                if hvb_power < get_state_value(Hash.HvbPowerMin, 9999999.0):
                    set_state(Hash.HvbPowerMin, hvb_power)
                    arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.HvbPowerMin)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: Minimum HVB power seen: {hvb_power} W (calculated)")

                interval = (interval_end - interval_start) * 0.000000001
                delta_hvb_energy = (hvb_power_interval_start * interval) / 3600
                hvb_energy = int(get_state_value(Hash.HvbEnergy, 0.0) + delta_hvb_energy)
                set_state(Hash.HvbEnergy, hvb_energy)
                arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.HvbEnergy)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': hvb_energy})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: HVB energy: {hvb_energy} Wh (calculated)")

                if delta_hvb_energy < 0:
                    hvb_energy_gained = int(get_state_value(Hash.HvbEnergyGained, 0.0) + delta_hvb_energy)
                    set_state(Hash.HvbEnergyGained, hvb_energy_gained)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: HVB energy gained: {hvb_energy_gained} Wh (calculated)")
                else:
                    hvb_energy_lost = int(get_state_value(Hash.HvbEnergyLost, 0.0) + delta_hvb_energy)
                    set_state(Hash.HvbEnergyLost, hvb_energy_lost)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: HVB energy lost: {hvb_energy_lost} Wh (calculated)")

            elif synthetic_hash == Hash.LvbPower:
                lvb_power_interval_start, interval_start = get_state(Hash.LvbPower, 0.0)

                lvb_power = int(get_state_value(Hash.LvbVoltage, 0.0) * get_state_value(Hash.LvbCurrent, 0.0))
                interval_end = set_state_interval(Hash.LvbPower, lvb_power)
                arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.LvbPower)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': lvb_power})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: LVB power: {lvb_power} W (calculated)")

                interval = (interval_end - interval_start) * 0.000000001
                delta_lvb_energy = (lvb_power_interval_start * interval) / 3600
                lvb_energy = int(get_state_value(Hash.LvbEnergy, 0.0) + delta_lvb_energy)
                set_state(Hash.LvbEnergy, lvb_energy)
                arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.LvbEnergy)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': lvb_energy})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: LVB energy: {lvb_energy} Wh (calculated)")

            elif synthetic_hash == Hash.ChargerInputPower:
                charger_input_power_interval_start, interval_start = get_state(Hash.ChargerInputPower, 0.0)

                charger_input_power = int(get_state_value(Hash.ChargerInputVoltage, 0.0) * get_state_value(Hash.ChargerInputCurrent, 0.0))
                interval_end = set_state_interval(Hash.ChargerInputPower, charger_input_power)
                arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.ChargerInputPower)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': charger_input_power})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger input power: {charger_input_power} W (calculated)")

                if charger_input_power > get_state_value(Hash.ChargerInputPowerMax, 0.0):
                    set_state(Hash.ChargerInputPowerMax, charger_input_power)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger maximum input power: {charger_input_power} W (calculated)")

                interval = (interval_end - interval_start) * 0.000000001
                charger_input_energy = int(get_state_value(Hash.ChargerInputEnergy, 0.0) + (charger_input_power_interval_start * interval) / 3600)
                set_state(Hash.ChargerInputEnergy, charger_input_energy)
                arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.ChargerInputEnergy)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': charger_input_energy})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger input energy: {charger_input_energy} Wh (calculated)")

            elif synthetic_hash == Hash.ChargerOutputPower:
                charger_output_power_interval_start, interval_start = get_state(Hash.ChargerOutputPower, 0.0)

                charger_output_power = int(get_state_value(Hash.ChargerOutputVoltage, 0.0) * get_state_value(Hash.ChargerOutputCurrent, 0.0))
                interval_end = set_state_interval(Hash.ChargerOutputPower, charger_output_power)
                arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.ChargerOutputPower)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': charger_output_power})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger output power: {charger_output_power} W (calculated)")

                if charger_output_power > get_state_value(Hash.ChargerOutputPowerMax, 0.0):
                    set_state(Hash.ChargerOutputPowerMax, charger_output_power)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger maximum output power: {charger_output_power} W (calculated)")

                interval = (interval_end - interval_start) * 0.000000001
                charger_output_energy = int(get_state_value(Hash.ChargerOutputEnergy, 0.0) + (charger_output_power_interval_start * interval) / 3600)
                set_state(Hash.ChargerOutputEnergy, charger_output_energy)
                arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.ChargerOutputEnergy)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': charger_output_energy})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger output energy: {charger_output_energy} Wh (calculated)")

            elif synthetic_hash == Hash.HiresSpeedMax:
                hires_speed = get_state_value(Hash.HiresSpeed, 0.0)
                if hires_speed > get_state_value(Hash.HiresSpeedMax, 0.0):
                    set_state(Hash.HiresSpeedMax, hires_speed)
                    arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.HiresSpeedMax)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: Maximum speed seen: {hires_speed:.1f} kph (calculated)")

            elif synthetic_hash == Hash.GpsElevationMin:
                gps_elevation = get_state_value(Hash.GpsElevation, 0)
                if gps_elevation > get_state_value(Hash.GpsElevationMax, -99999999):
                    set_state(Hash.GpsElevationMax, gps_elevation)
                    arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.GpsElevationMax)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: Maximum GPS elevation seen: {gps_elevation} m (calculated)")
                if gps_elevation < get_state_value(Hash.GpsElevationMin, 99999999):
                    set_state(Hash.GpsElevationMin, gps_elevation)
                    arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.GpsElevationMin)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: Minimum GPS elevation seen: {gps_elevation} m (calculated)")

            elif synthetic_hash == Hash.ExtTemperatureSum:
                ext_sum_interval_start, interval_start = get_state(Hash.ExtTemperatureSum, 0)
                interval_minutes = int(((time_ns() - interval_start) * 0.000000001) / 60) + 1
                interval_minutes = interval_minutes if interval_start > 0 else 1
                ext_count = set_state(Hash.ExtTemperatureCount, get_state_value(Hash.ExtTemperatureCount, 0) + interval_minutes)
                ext_sum = set_state(Hash.ExtTemperatureSum, ext_sum_interval_start + get_state_value(Hash.ExteriorTemperature, 0) * interval_minutes)
                arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.ExtTemperatureSum)
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: Exterior temperature sum/count: {ext_sum}/{ext_count} (calculated)")

            elif synthetic_hash == Hash.WhPerKilometer:
                odometer_start = get_state_value(Hash.WhPerKilometerOdometerStart, -1)
                odometer_end = get_state_value(Hash.HiresOdometer, 0)
                set_state(Hash.WhPerKilometerOdometerStart, odometer_end)
                delta_odometer = odometer_end - odometer_start

                wh_start = get_state_value(Hash.WhPerKilometerStart, -1)
                wh_end = get_state_value(Hash.HvbEtE, 0)
                set_state(Hash.WhPerKilometerStart, wh_end)

                if wh_start >= 0:
                    delta_wh = wh_end - wh_start
                    wh_per_kilometer = int(delta_wh / delta_odometer)
                    set_state(Hash.WhPerKilometer, wh_per_kilometer)
                    arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.WhPerKilometer)
                    synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': wh_per_kilometer})
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: Efficiency: {wh_per_kilometer} Wh/km (calculated)")

            elif synthetic_hash == Hash.WhPerGpsSegment:
                wh_start = get_state_value(Hash.WhPerGpsSegmentStart, -1)
                wh_end = get_state_value(Hash.HvbEtE, 0)
                set_state(Hash.WhPerGpsSegmentStart, wh_end)
                if wh_start >= 0:
                    delta_wh = wh_end - wh_start
                    set_state(Hash.WhPerGpsSegment, delta_wh)
                    arbitration_id, did_id, synthetic_name = get_hash_fields(Hash.WhPerGpsSegment)
                    synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': delta_wh})
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: GPS segment efficiency: {delta_wh} Wh/segment (calculated)")

    except ValueError:
        _LOGGER.debug(f"ValueError in update_synthetics({hash.value})")
        pass
    return synthetics

