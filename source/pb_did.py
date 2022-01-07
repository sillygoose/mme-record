import struct
import json
#import logging

from typing import List

from exceptions import RuntimeError


#_LOGGER = logging.getLogger('mme')

"""
_DIDS = {
    0x1505: { 'name': 'HiresSpeed',             'packing': 'H',     'modules': ['PCM'],         'states': [{ 'name': 'speed', 'value': 0}] },
    0x1E12: { 'name': 'GearCommanded',          'packing': 'B',     'modules': ['SOBDM'],       'states': [{ 'name': 'gear_commanded', 'value': 70}] },
    0x4028: { 'name': 'LvbSoc',                 'packing': 'B',     'modules': ['BCM'],         'states': [{ 'name': 'lvb_soc', 'value': 0x5B}] },
    0x402A: { 'name': 'LvbVoltage',             'packing': 'B',     'modules': ['BCM'],         'states': [{ 'name': 'lvb_voltage', 'value': 0x92}] },
    0x402B: { 'name': 'LvbCurrent',             'packing': 'B',     'modules': ['BCM'],         'states': [{ 'name': 'lvb_current', 'value': 0x82}] },
    0x404C: { 'name': 'HiresOdometer',          'packing': 'T',     'modules': ['IPC'],         'states': [{ 'name': 'odometer', 'value': 0xdcdc}] },
    0x411F: { 'name': 'KeyState',               'packing': 'B',     'modules': ['APIM', 'GWM'], 'states': [{ 'name': 'key_state', 'value': 5}] },
    0x4800: { 'name': 'HvbTemp',                'packing': 'B',     'modules': ['BECM'],        'states': [{ 'name': 'hvb_temp', 'value': 0x40}] },
    0x4801: { 'name': 'HvbSoc',                 'packing': 'H',     'modules': ['BECM'],        'states': [{ 'name': 'hvb_soc', 'value': 0x7A86}] },
    0x480D: { 'name': 'HvbVoltage',             'packing': 'H',     'modules': ['BECM'],        'states': [{ 'name': 'hvb_voltage', 'value': 0x8ABD}] },
    0x4836: { 'name': 'LvbLvCurrent',           'packing': 'B',     'modules': ['DCDC'],        'states': [{ 'name': 'lvb_lv_current', 'value': 0x1B}] },
    0x483A: { 'name': 'LvbHvCurrent',           'packing': 'B',     'modules': ['DCDC'],        'states': [{ 'name': 'lvb_hv_current', 'value': 0x3A}] },
    0x483D: { 'name': 'LvbDcdcEnable',          'packing': 'H',     'modules': ['DCDC'],        'states': [{ 'name': 'lvb_dcdc_enable', 'value': 0x186}] },
    0x4842: { 'name': 'HvbChrgCurrentReqsted',  'packing': 'h',     'modules': ['SOBDM'],       'states': [{ 'name': 'hvb_chrg_current_reqsted', 'value': 1000}] },
    0x4844: { 'name': 'HvbChrgVoltageReqsted',  'packing': 'B',     'modules': ['SOBDM'],       'states': [{ 'name': 'hvb_chrg_voltage_reqsted', 'value': 10}] },
    0x4845: { 'name': 'HvbSocD',                'packing': 'B',     'modules': ['BECM'],        'states': [{ 'name': 'hvb_socd', 'value': 0x84}] },
    0x4848: { 'name': 'EnergyToEmpty',          'packing': 'H',     'modules': ['BECM'],        'states': [{ 'name': 'energy_to_empty', 'value': 0x63C5}] },
    0x484A: { 'name': 'ChargerOutputVoltage',   'packing': 'h',     'modules': ['SOBDM'],       'states': [{ 'name': 'charger_output_voltage', 'value': 1000}] },
    0x484E: { 'name': 'ChargerInputPower',      'packing': 'h',     'modules': ['SOBDM'],       'states': [{ 'name': 'charger_input_power', 'value': 1000}] },
    0x484F: { 'name': 'ChargerStatus',          'packing': 'B',     'modules': ['BECM'],        'states': [{ 'name': 'charger_status', 'value': 0x03}] },
    0x4850: { 'name': 'ChargerOutputCurrent',   'packing': 'h',     'modules': ['SOBDM'],       'states': [{ 'name': 'charger_output_current', 'value': 1000}] },
    0x4851: { 'name': 'EvseType',               'packing': 'B',     'modules': ['BECM'],        'states': [{ 'name': 'evse_type', 'value': 0x06}] },
    0x485E: { 'name': 'ChargerInputVoltage',    'packing': 'H',     'modules': ['SOBDM'],       'states': [{ 'name': 'charger_input_voltage', 'value': 1000}] },
    0x485F: { 'name': 'ChargerInputCurrent',    'packing': 'B',     'modules': ['SOBDM'],       'states': [{ 'name': 'charger_input_current', 'value': 100}] },
    0x4860: { 'name': 'ChargerInputFrequency',  'packing': 'B',     'modules': ['SOBDM'],       'states': [{ 'name': 'charger_input_freq', 'value': 100}] },
    0x4861: { 'name': 'ChargerPilotDutyCycle',  'packing': 'B',     'modules': ['SOBDM'],       'states': [{ 'name': 'charger_pilot_duty_cycle', 'value': 100}] },
    0x48B6: { 'name': 'ChargerPilotVoltage',    'packing': 'B',     'modules': ['SOBDM'],       'states': [{ 'name': 'charger_pilot_voltage', 'value': 100}] },
    0x48BC: { 'name': 'HvbMaxChargeCurrent',    'packing': 'h',     'modules': ['SOBDM'],       'states': [{ 'name': 'hvb_max_charge_current', 'value': 100}] },
    0x48C4: { 'name': 'ChargerMaxPower',        'packing': 'H',     'modules': ['SOBDM'],       'states': [{ 'name': 'ChargerMaxPower', 'value': 100}] },
    0x48F9: { 'name': 'HvbCurrent',             'packing': 'h',     'modules': ['BECM'],        'states': [{ 'name': 'hvb_current', 'value': 0x0052}] },
    0x48FB: { 'name': 'ChargerPowerLimit',      'packing': 'h',     'modules': ['BECM'],        'states': [{ 'name': 'charger_power_limit', 'value': -1}] },
    0x490C: { 'name': 'HvbSoh',                 'packing': 'B',     'modules': ['BECM'],        'states': [{ 'name': 'hvb_soh', 'value': 0xC8}] },
    0x6310: { 'name': 'GearDisplayed',          'packing': 'B',     'modules': ['IPC'],         'states': [{ 'name': 'gear_displayed', 'value': 0}] },
    0x8012: { 'name': 'GPS',                    'packing': 'HllBHH','modules': ['APIM'],        'states': [
                                                                                                        { 'name': 'elevation', 'value': 100},
                                                                                                        { 'name': 'latitude', 'value': 2577},
                                                                                                        { 'name': 'longitude', 'value': -4610},
                                                                                                        { 'name': 'fix', 'value': 4},
                                                                                                        { 'name': 'speed', 'value': 12},
                                                                                                        { 'name': 'heading', 'value': 256},
                                                                                                    ]},
    0xDD00: { 'name': 'Time',                   'packing': 'I',     'modules': ['SOBDM'],       'states': [{ 'name': 'time', 'value': 0}] },
    0xDD04: { 'name': 'InteriorTemp',           'packing': 'B',     'modules': ['SOBDM'],       'states': [{ 'name': 'interior_temp', 'value': 50}] },
    0xDD05: { 'name': 'ExteriorTemp',           'packing': 'B',     'modules': ['SOBDM'],       'states': [{ 'name': 'exterior_temp', 'value': 50}] },
}
"""


class DID:

    def __init__(self, did: int, name: str, packing: str, modules: List[str], states: List[dict]) -> None:
        self._did = did
        self._name = name
        self._packing = packing
        self._modules = modules
        self._states = []
        for state in states:
            # variable = state.get('name', None)
            value = state.get('value', None)
            self._states.append(value)

    def response(self) -> bytearray:
        response = bytearray()
        index = 0
        for state in self._states:
            if self._packing[index] == 'T':
                packing_format = '>L'
            elif self._packing[index] == 't':
                packing_format = '>l'
            else:
                packing_format = '>' + self._packing[index]
            postfix = struct.pack(packing_format, state)
            if self._packing[index] == 'T' or self._packing[index] == 't':
                # Pack as uint then remove high order byte to get A:B:C
                postfix = postfix[1:4]
            response = response + postfix
            index += 1
        return response

    def new_event(self, event) -> None:
        payload = bytearray(event.get('payload'))
        unpacking_format = '>' + self._packing
        if self._packing.find('T') >= 0:
            unpacking_format = unpacking_format.replace('T', 'HB')
        unpacked_values = list(struct.unpack(unpacking_format, payload))
        if self._packing.find('T') >= 0:
            unpacked_values[0] = unpacked_values[0] * 256 + unpacked_values[1]
        index = 0
        for _ in self._states:
            self._states[index] = unpacked_values[index]
            index += 1

    def did(self) -> int:
        return self._did

    def name(self) -> str:
        return self._name

    def packing(self) -> str:
        return self._packing

    def used_in(self) -> List[str]:
        return self._modules

    def _dids_organized_by_name(dids: List[dict]) -> dict:
        dids_by_names = {}
        for did in dids:
            dids_by_names[did.get('name')] = did
        return dids_by_names

    def _dids_organized_by_did(dids: List[dict]) -> dict:
        dids_by_id = {}
        for did in dids:
            dids_by_id[did.get('did')] = did
        return dids_by_id

    def _load_dids(file: str) -> dict:
        with open(file) as infile:
            try:
                dids = json.load(infile)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON error in '{file}' at line {e.lineno}")
        return dids

    def _dump_dids(file: str, dids: dict) -> None:
        json_dids = json.dumps(dids, indent = 4, sort_keys=False)
        with open(file, "w") as outfile:
            outfile.write(json_dids)

    # DID static data
    _supported_dids = _load_dids(file='json/mme_dids.json')

    def pb_dids() -> List[dict]:
        return DID._supported_dids
