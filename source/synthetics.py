import logging
#from time import time_ns

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
                hvb_power = get_state_value(Hash.HvbVoltage, 0.0) * get_state_value(Hash.HvbCurrent, 0.0)
                set_state(Hash.HvbPower, hvb_power)
                arbitration_id, did_id, synthetic_name = hash_fields(Hash.HvbPower)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': hvb_power})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: HVB power is {hvb_power:.0f} W (calculated)")
            elif synthetic_hash == Hash.LvbPower:
                lvb_power = get_state_value(Hash.LvbVoltage, 0.0) * get_state_value(Hash.LvbCurrent, 0.0)
                set_state(Hash.LvbPower, lvb_power)
                arbitration_id, did_id, synthetic_name = hash_fields(Hash.LvbPower)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': lvb_power})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: LVB power is {lvb_power:.0f} W (calculated)")
            elif synthetic_hash == Hash.ChargerInputPower:
                charger_input_power = get_state_value(Hash.ChargerInputVoltage, 0.0) * get_state_value(Hash.ChargerInputCurrent, 0.0)
                set_state(Hash.ChargerInputPower, charger_input_power)
                arbitration_id, did_id, synthetic_name = hash_fields(Hash.ChargerInputPower)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': charger_input_power})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger input power is {charger_input_power:.0f} W (calculated)")
            elif synthetic_hash == Hash.ChargerOutputPower:
                charger_output_power = get_state_value(Hash.ChargerOutputVoltage, 0.0) * get_state_value(Hash.ChargerOutputCurrent, 0.0)
                set_state(Hash.ChargerOutputPower, charger_output_power)
                arbitration_id, did_id, synthetic_name = hash_fields(Hash.ChargerOutputPower)
                synthetics.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': charger_output_power})
                _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger output power is {charger_output_power:.0f} W (calculated)")
    except ValueError:
        _LOGGER.debug(f"ValueError in update_synthetics({hash.value})")
    return synthetics

