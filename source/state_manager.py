"""
State definitions
"""
import logging
from queue import PriorityQueue
from time import time
import json

from enum import Enum, unique
from typing import List

from codec_manager import *
from did import KeyState, ChargingStatus, EvseType, GearCommanded, RemoteStart


_LOGGER = logging.getLogger('mme')


@unique
class VehicleState(Enum):
        Unknown = 0                 # initial state until another is determined
        Sleeping = 1                # only the GWM responds to ReadDID requests
        Off = 2                     # the vehicle was turned off (but modules are still responding)
        Accessories = 3             # the vehicle start button was pressed with the brake not depressed
        Starting = 4                # this is an intermediate state seen when the start button is held closed (likely insignificant)
        On = 5                      # the vehicle start button was pressed with the brake depressed
        Trip = 6                    # the vehicle is in a gear other than Park
        Preconditioning = 7         # the vehicle is preconditioning
        PluggedIn = 8               # the vehicle has plugged in
        AC_Charging = 9             # the vehicle is AC charging
        DC_Charging = 10            # the vehicle is DC fast charging


@unique
class Hash(Enum):
    KeyState            = '0716:411F:key_state'
    EvseType            = '07E4:4851:evse_type'
    ChargingStatus      = '07E4:484D:charging_status'
    GearCommanded       = '07E2:1E12:gear_commanded'
    HvbVoltage          = '07E4:480D:hvb_voltage'
    HvbCurrent          = '07E4:48F9:hvb_current'
    HvbPower            = '4096:4096:hvb_power'
    LvbVoltage          = '0726:402A:lvb_voltage'
    LvbCurrent          = '0726:402B:lvb_current'
    LvbPower            = '4096:4097:lvb_power'
    RemoteStart         = '0726:41B9:remote_start'


class StateManager:

    _state_file_lookup = {
        VehicleState.Unknown:           {'state_file': 'json/unknown.json',     'state_keys': [Hash.KeyState]},
        VehicleState.Off:               {'state_file': 'json/off.json',         'state_keys': [Hash.KeyState, Hash.ChargingStatus, Hash.RemoteStart]},
        VehicleState.On:                {'state_file': 'json/on.json',          'state_keys': [Hash.KeyState, Hash.ChargingStatus, Hash.GearCommanded]},
        VehicleState.PluggedIn:         {'state_file': 'json/charging.json',    'state_keys': [Hash.ChargingStatus, Hash.EvseType]},
        VehicleState.AC_Charging:       {'state_file': 'json/ac_charging.json', 'state_keys': [Hash.ChargingStatus]},
        VehicleState.Trip:              {'state_file': 'json/trip.json',        'state_keys': [Hash.GearCommanded]},

        #VehicleState.Sleeping:          {'state_file': 'json/sleeping.json',    'state_keys': ['0716:411F:key_state', '07E4:484D:charging_status']},
        #VehicleState.Preconditioning:   'json/preconditioning.json',
        #VehicleState.DC_Charging:       'json/dc_charging.json',
    }

    def __init__(self) -> None:
        self._codec_manager = CodecManager()
        self._command_queue = PriorityQueue()
        state_functions = {
            VehicleState.Unknown: self.unknown,
            VehicleState.Off: self.off,
            VehicleState.On: self.on,
            VehicleState.PluggedIn: self.plugged_in,
            VehicleState.AC_Charging: self.ac_charging,
            VehicleState.Trip: self.trip,
        }
        for k, v in StateManager._state_file_lookup.items():
            v['state_function'] = state_functions.get(k)

    def start(self) -> None:
        self.change_state(VehicleState.Unknown)
        self._vehicle_state = {}

    def stop(self) -> None:
        pass

    def _load_state_definition(self, file: str) -> List[dict]:
        with open(file) as infile:
            try:
                state_definition = json.load(infile)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"JSON error in '{file}' at line {e.lineno}")
            except FileNotFoundError as e:
                raise RuntimeError(f"{e}")

        for module in state_definition:
            dids = module.get('dids')
            for did in dids:
                codec_id = did.get('codec_id')
                codec = self._codec_manager.codec(codec_id)
                did['codec'] = codec
        return state_definition

    def _load_queue(self, module_read_commands: List[dict]) -> None:
        for module in module_read_commands:
            enable = module.get('enable', True)
            if enable:
                period = module.get('period', 5)
                payload = (time(), period, [module])
                self._command_queue.put(payload)

    def get_current_state_file(self) -> str:
        return StateManager._state_file_lookup.get(self._state).get('state_file')

    def get_state_file(self, state:VehicleState) -> str:
        return StateManager._state_file_lookup.get(state).get('state_file')

    def _get_state_keys(self) -> List[str]:
        return StateManager._state_file_lookup.get(self._state).get('state_keys')

    def change_state(self, new_state: VehicleState) -> None:
        self._state = new_state
        self._state_file = StateManager._state_file_lookup.get(new_state).get('state_file')
        self._state_function = StateManager._state_file_lookup.get(new_state).get('state_function')
        while not self._command_queue.empty():
            self._command_queue.get_nowait()
            self._command_queue.task_done()
        queue_commands = self._load_state_definition(self._state_file)
        self._load_queue(queue_commands)
        _LOGGER.info(f"Vehicle state changed to '{self._state.name}'")

    def _calculate_synthetic(self, hash: str) -> None:
        synthetic = None
        try:
            hash = Hash(hash)
            if hash == Hash.HvbVoltage or hash == Hash.HvbCurrent:
                hvb_voltage = self._vehicle_state.get(Hash.HvbVoltage.value, 0.0)
                hvb_current = self._vehicle_state.get(Hash.HvbCurrent.value, 0.0)
                hvb_power = hvb_voltage * hvb_current
                self._vehicle_state[Hash.HvbPower] = hvb_power
                hash_field = Hash.HvbPower.value.split(':')
                synthetic = {'arbitration_id': int(hash_field[0]), 'did_id': int(hash_field[1]), 'name': hash_field[2], 'value': hvb_power}
                _LOGGER.debug(f"Calculated 'HvbPower' is {hvb_power:.0f} W from {hvb_voltage:.1f} * {hvb_current:.1f}")
            elif hash == Hash.LvbVoltage or hash == Hash.LvbCurrent:
                lvb_voltage = self._vehicle_state.get(Hash.LvbVoltage.value, 0.0)
                lvb_current = self._vehicle_state.get(Hash.LvbCurrent.value, 0.0)
                lvb_power = lvb_voltage * lvb_current
                hash_field = Hash.LvbPower.value.split(':')
                synthetic = {'arbitration_id': int(hash_field[0]), 'did_id': int(hash_field[1]), 'name': hash_field[2], 'value': lvb_power}
                self._vehicle_state[Hash.LvbPower] = lvb_power
                _LOGGER.debug(f"Calculated 'LvbPower' is {lvb_power:.0f} W from {lvb_voltage:.1f} * {lvb_current:.f}")
        except ValueError:
            pass
        return synthetic

    def update_vehicle_state(self, state_change: dict) -> List[dict]:
        state_data = []
        if state_change.get('type', None) is None:
            did_id = state_change.get('did_id', None)
            if did_id:
                codec = self._codec_manager.codec(did_id)
                decoded_playload = codec.decode(None, bytearray(state_change.get('payload')))
                arbitration_id = state_change.get('arbitration_id')
                states = decoded_playload.get('states')
                for state in states:
                    for state_name, state_value in state.items():
                        hash = f"{arbitration_id:04X}:{did_id:04X}:{state_name}"
                        self._last_state_change = hash
                        self._vehicle_state[hash] = state_value
                        state_data.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': state_name, 'value': state_value})
                        synthetic = self._calculate_synthetic(hash)
                        if synthetic:
                            state_data.append(synthetic)
                _LOGGER.debug(self._last_state_change)
                self._state_function()
        return state_data

    def _get_KeyState(self, key: Hash) -> KeyState:
        key_state = None
        if self._last_state_change == key.value and key == Hash.KeyState:
            try:
                key_state = KeyState(self._vehicle_state.get(Hash.KeyState.value))
            except ValueError:
                _LOGGER.info(f"While in '{self._state.name}', 'KeyState' had an unexpected value: {self._vehicle_state.get(Hash.KeyState.value)}")
        return key_state

    def _get_ChargingStatus(self, key: Hash) -> ChargingStatus:
        charging_status = None
        if self._last_state_change == key.value and key == Hash.ChargingStatus:
            try:
                charging_status = ChargingStatus(self._vehicle_state.get(Hash.ChargingStatus.value))
            except ValueError:
                _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' had an unexpected value: {self._vehicle_state.get(Hash.ChargingStatus.value)}")
        return charging_status

    def _get_GearCommanded(self, key: Hash) -> GearCommanded:
        gear_commanded = None
        if self._last_state_change == key.value and key == Hash.GearCommanded:
            try:
                gear_commanded = GearCommanded(self._vehicle_state.get(Hash.GearCommanded.value))
            except ValueError:
                _LOGGER.info(f"While in '{self._state.name}', 'GearCommanded' had an unexpected value: {self._vehicle_state.get(Hash.GearCommanded.value)}")
        return gear_commanded

    def _get_EvseType(self, key: Hash) -> EvseType:
        evse_type = None
        if self._last_state_change == key.value and key == Hash.EvseType:
            try:
                evse_type = EvseType(self._vehicle_state.get(Hash.EvseType.value))
            except ValueError:
                _LOGGER.info(f"While in '{self._state.name}', 'EvseType' had an unexpected value: {self._vehicle_state.get(Hash.EvseType.value)}")
        return evse_type

    def _get_RemoteStart(self, key: Hash) -> RemoteStart:
        remote_start = None
        if self._last_state_change == key.value and key == Hash.RemoteStart:
            try:
                remote_start = RemoteStart(self._vehicle_state.get(Hash.RemoteStart.value))
            except ValueError:
                _LOGGER.info(f"While in '{self._state.name}', 'RemoteStart' had an unexpected value: {self._vehicle_state.get(Hash.RemoteStart.value)}")
        return remote_start

    def unknown(self) -> None:
        for key in self._get_state_keys():
            if key_state := self._get_KeyState(key):
                if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                    self.change_state(VehicleState.Off)
                elif key_state == KeyState.On or key_state == KeyState.Cranking:
                    self.change_state(VehicleState.On)
        assert self._state != VehicleState.Unknown

    def off(self) -> None:
        for key in self._get_state_keys():
            if key_state := self._get_KeyState(key):
                if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                    pass
                elif key_state == KeyState.On or key_state == KeyState.Cranking:
                    self.change_state(VehicleState.On)
            elif charging_status := self._get_ChargingStatus(key):
                if charging_status == ChargingStatus.Charging:
                    self.change_state(VehicleState.PluggedIn)
                elif charging_status == ChargingStatus.Wait:
                    pass
                elif charging_status != ChargingStatus.NotReady:
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' returned an unexpected response: {charging_status}")
            elif remote_start := self._get_RemoteStart(key):
                if remote_start == RemoteStart.On:
                    self.change_state(VehicleState.On)

    def on(self) -> None:
        for key in self._get_state_keys():
            if key_state := self._get_KeyState(key):
                if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                    self.change_state(VehicleState.Off)
                elif key_state == KeyState.On or key_state == KeyState.Cranking:
                    pass
            elif charging_status := self._get_ChargingStatus(key):
                if charging_status == ChargingStatus.Charging:
                    self.change_state(VehicleState.PluggedIn)
                elif charging_status == ChargingStatus.Wait:
                    pass
                elif charging_status != ChargingStatus.NotReady:
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' returned an unexpected response: {charging_status}")
            elif gear_commanded := self._get_GearCommanded(key):
                if gear_commanded != GearCommanded.Park:
                    self.change_state(VehicleState.Trip)

    def trip(self) -> None:
        for key in self._get_state_keys():
            if gear_commanded := self._get_GearCommanded(key):
                if gear_commanded == GearCommanded.Park:
                    self.change_state(VehicleState.On)

    def plugged_in(self) -> None:
        for key in self._get_state_keys():
            if charging_status := self._get_ChargingStatus(key):
                if charging_status == ChargingStatus.Charging:
                    pass
                elif charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Done:
                    if key_state := self._get_KeyState(Hash.KeyState):
                        if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                            self.change_state(VehicleState.Off)
                        elif key_state == KeyState.On or key_state == KeyState.Cranking:
                            self.change_state(VehicleState.On)
                else:
                    _LOGGER.info(f"While {self._state}, 'ChargingStatus' returned an unexpected response: {charging_status}")
            if evse_type := self._get_EvseType(key):
                if evse_type == EvseType.BasAC:
                    self.change_state(VehicleState.AC_Charging)
                elif evse_type != EvseType.NoType:
                    _LOGGER.info(f"While in '{self._state.name}', 'EvseType' returned an unexpected response: {evse_type}")

    def ac_charging(self) -> None:
        for key in self._get_state_keys():
            if charging_status := self._get_ChargingStatus(key):
                if charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Done:
                    if key_state := self._get_KeyState(Hash.KeyState):
                        if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                            self.change_state(VehicleState.Off)
                        elif key_state == KeyState.On or key_state == KeyState.Cranking:
                            self.change_state(VehicleState.On)
                else:
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' returned an unexpected response: {charging_status}")
