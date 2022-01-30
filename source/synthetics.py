import logging

from typing import List

from state_engine import get_state, get_state_value, set_state, hash_fields
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
    }


def update_synthetics(hash: Hash) -> List[dict]:
    synthetics = []
    try:
        if synthetic_hash := Synthetics._synthetic_hashes.get(Hash(hash), None):
            if synthetic_hash == Hash.HvbPower:
                hvb_power_interval_start, interval_start = get_state(Hash.HvbPower, 0.0)

                hvb_power = get_state_value(Hash.HvbVoltage, 0.0) * get_state_value(Hash.HvbCurrent, 0.0)
                interval_end = set_state(Hash.HvbPower, hvb_power)
                arbitration_id, did_id, synthetic_name = hash_fields(Hash.HvbPower)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': hvb_power})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: HVB power is {hvb_power:.0f} W (calculated)")

                interval = (interval_end - interval_start) * 0.000000001
                hvb_energy = get_state_value(Hash.HvbEnergy, 0.0)
                hvb_energy += (hvb_power_interval_start * interval) / 3600
                set_state(Hash.HvbEnergy, hvb_energy)
                arbitration_id, did_id, synthetic_name = hash_fields(Hash.HvbEnergy)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': hvb_energy})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: HVB energy is {hvb_energy:.0f} Wh (calculated)")
            elif synthetic_hash == Hash.LvbPower:
                lvb_power_interval_start, interval_start = get_state(Hash.LvbPower, 0.0)

                lvb_power = get_state_value(Hash.LvbVoltage, 0.0) * get_state_value(Hash.LvbCurrent, 0.0)
                interval_end = set_state(Hash.LvbPower, lvb_power)
                arbitration_id, did_id, synthetic_name = hash_fields(Hash.LvbPower)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': lvb_power})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: LVB power is {lvb_power:.0f} W (calculated)")

                interval = (interval_end - interval_start) * 0.000000001
                lvb_energy = get_state_value(Hash.LvbEnergy, 0.0)
                lvb_energy += (lvb_power_interval_start * interval) / 3600
                set_state(Hash.LvbEnergy, lvb_energy)
                arbitration_id, did_id, synthetic_name = hash_fields(Hash.LvbEnergy)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': lvb_energy})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: LVB energy is {lvb_energy:.0f} Wh (calculated)")
            elif synthetic_hash == Hash.ChargerInputPower:
                charger_input_power_interval_start, interval_start = get_state(Hash.ChargerInputPower, 0.0)

                charger_input_power = get_state_value(Hash.ChargerInputVoltage, 0.0) * get_state_value(Hash.ChargerInputCurrent, 0.0)
                interval_end = set_state(Hash.ChargerInputPower, charger_input_power)
                arbitration_id, did_id, synthetic_name = hash_fields(Hash.ChargerInputPower)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': charger_input_power})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger input power is {charger_input_power:.0f} W (calculated)")

                interval = (interval_end - interval_start) * 0.000000001
                charger_input_energy_in = get_state_value(Hash.ChargerInputEnergy, 0.0)
                charger_input_energy_delta = (charger_input_power_interval_start * interval) / 3600
                charger_input_energy = charger_input_energy_in + charger_input_energy_delta
                set_state(Hash.ChargerInputEnergy, charger_input_energy)
                arbitration_id, did_id, synthetic_name = hash_fields(Hash.ChargerInputEnergy)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': charger_input_energy})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger input energy is {charger_input_energy:.0f} Wh (calculated)")
            elif synthetic_hash == Hash.ChargerOutputPower:
                charger_output_power_interval_start, interval_start = get_state(Hash.ChargerOutputPower, 0.0)

                charger_output_power = get_state_value(Hash.ChargerOutputVoltage, 0.0) * get_state_value(Hash.ChargerOutputCurrent, 0.0)
                interval_end = set_state(Hash.ChargerOutputPower, charger_output_power)
                arbitration_id, did_id, synthetic_name = hash_fields(Hash.ChargerOutputPower)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': charger_output_power})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger output power is {charger_output_power:.0f} W (calculated)")

                interval = (interval_end - interval_start) * 0.000000001
                charger_output_energy = get_state_value(Hash.ChargerOutputEnergy, 0.0)
                charger_output_energy += (charger_output_power_interval_start * interval) / 3600
                set_state(Hash.ChargerOutputEnergy, charger_output_energy)
                arbitration_id, did_id, synthetic_name = hash_fields(Hash.ChargerOutputEnergy)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': charger_output_energy})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger output energy is {charger_output_energy:.0f} Wh (calculated)")

    except ValueError:
        _LOGGER.debug(f"ValueError in update_synthetics({hash.value})")
        pass
    return synthetics

