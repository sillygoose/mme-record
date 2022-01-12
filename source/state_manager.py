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
from did import KeyState, ChargingStatus, EvseType, GearCommanded


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
    HvbVoltage          = '07E4:4851:hvb_voltage'
    HvbCurrent          = '07E4:4851:hvb_current'
    HvbPower            = 'hvb:hvb_power'
    LvbVoltage          = '0726:402A:lvb_voltage'
    LvbCurrent          = '0726:402B:lvb_current'
    LvbPower            = 'lvb:lvb_power'


class StateManager:

    _state_file_lookup = {
        VehicleState.Unknown:           {'state_file': 'json/unknown.json',     'state_keys': [Hash.KeyState]},
        VehicleState.Off:               {'state_file': 'json/off.json',         'state_keys': [Hash.KeyState, Hash.ChargingStatus]},
        VehicleState.On:                {'state_file': 'json/on.json',          'state_keys': [Hash.KeyState, Hash.ChargingStatus, Hash.GearCommanded]},
        VehicleState.PluggedIn:         {'state_file': 'json/charging.json',    'state_keys': [Hash.ChargingStatus, Hash.EvseType]},
        VehicleState.AC_Charging:       {'state_file': 'json/ac_charging.json', 'state_keys': [Hash.ChargingStatus]},
        VehicleState.Trip:              {'state_file': 'json/trip.json',        'state_keys': [Hash.GearCommanded]},

        #VehicleState.Sleeping:          {'state_file': 'json/sleeping.json',    'state_keys': ['0716:411F:key_state', '07E4:484D:charging_status']},
        #VehicleState.Preconditioning:   'json/preconditioning.json',
        #VehicleState.DC_Charging:       'json/dc_charging.json',
    }

    def __init__(self, config: dict) -> None:
        self._config = config
        self._codec_manager = CodecManager(config=self._config)
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

        self.change_state(VehicleState.Unknown)
        self._vehicle_state = {}

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
        try:
            hash = Hash(hash)
            if hash == Hash.HvbVoltage or hash == Hash.HvbCurrent:
                hvb_voltage = self._vehicle_state.get(Hash.HvbVoltage.value, 0.0)
                hvb_current = self._vehicle_state.get(Hash.HvbCurrent.value, 0.0)
                hvb_power = hvb_voltage * hvb_current
                self._vehicle_state[Hash.HvbPower] = hvb_power
                _LOGGER.info(f"Calculated 'HvbPower' is {hvb_power:.0f} from {hvb_voltage:.1f} {hvb_current:.1f}")
        except ValueError:
            pass

    def update_vehicle_state(self, state_change: dict) -> None:
        if state_change.get('type', None) is None:
            did_id = state_change.get('did_id', None)
            if did_id:
                codec = self._codec_manager.codec(did_id)
                decoded_playload = codec.decode(None, bytearray(state_change.get('payload')))
                arbitration_id = state_change.get('arbitration_id')
                states = decoded_playload.get('states')
                for state in states:
                    for k, v in state.items():
                        hash = f"{arbitration_id:04X}:{did_id:04X}:{k}"
                        self._last_state_change = hash
                        self._vehicle_state[hash] = v
                        self._calculate_synthetic(hash)
                _LOGGER.debug(self._last_state_change)
                self._state_function()

    def unknown(self) -> None:
        for key in self._get_state_keys():
            if self._last_state_change == key.value and key == Hash.KeyState:
                try:
                    key_state = KeyState(self._vehicle_state.get(Hash.KeyState.value))
                except ValueError:
                    _LOGGER.info(f"While in '{self._state.name}', 'KeyState' had an unexpected value: {self._vehicle_state.get(Hash.KeyState.value)}")
                    continue
                if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                    self.change_state(VehicleState.Off)
                elif key_state == KeyState.On:
                    self.change_state(VehicleState.On)
                else:
                    _LOGGER.info(f"While in '{self._state.name}', 'KeyState' returned an unexpected response: {key_state}")

    def off(self) -> None:
        for key in self._get_state_keys():
            if self._last_state_change == key.value and key == Hash.KeyState:
                try:
                    key_state = KeyState(self._vehicle_state.get(Hash.KeyState.value))
                except ValueError:
                    _LOGGER.info(f"While in '{self._state.name}', 'KeyState' had an unexpected value: {self._vehicle_state.get(Hash.KeyState.value)}")
                    continue
                if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                    pass
                elif key_state == KeyState.On or key_state == KeyState.Cranking:
                    self.change_state(VehicleState.On)
                else:
                    _LOGGER.info(f"While in '{self._state.name}', 'KeyState' returned an unexpected response: {key_state}")
            elif self._last_state_change == key.value and key == Hash.ChargingStatus:
                try:
                    charging_status = ChargingStatus(self._vehicle_state.get(Hash.ChargingStatus.value))
                except ValueError:
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' had an unexpected value: {self._vehicle_state.get(Hash.ChargingStatus.value)}")
                    continue
                if charging_status == ChargingStatus.Charging:
                    self.change_state(VehicleState.PluggedIn)
                elif charging_status == ChargingStatus.Wait:
                    pass
                elif charging_status != ChargingStatus.NotReady:
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' returned an unexpected response: {charging_status}")

    def on(self) -> None:
        for key in self._get_state_keys():
            if self._last_state_change == key.value and key == Hash.KeyState:
                try:
                    key_state = KeyState(self._vehicle_state.get(Hash.KeyState.value))
                except ValueError:
                    _LOGGER.info(f"While in '{self._state.name}', 'KeyState' had an unexpected value: {self._vehicle_state.get(Hash.KeyState.value)}")
                    continue
                if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                    self.change_state(VehicleState.Off)
                elif key_state == KeyState.On or key_state == KeyState.Cranking:
                    pass
                else:
                    _LOGGER.info(f"While in '{self._state.name}', 'KeyState' returned an unexpected response: {key_state}")
            elif self._last_state_change == key.value and key == Hash.ChargingStatus:
                try:
                    charging_status = ChargingStatus(self._vehicle_state.get(Hash.ChargingStatus.value))
                except ValueError:
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' had an unexpected value: {self._vehicle_state.get(Hash.ChargingStatus.value)}")
                    continue
                if charging_status == ChargingStatus.Charging:
                    self.change_state(VehicleState.PluggedIn)
                elif charging_status == ChargingStatus.Wait:
                    pass
                elif charging_status != ChargingStatus.NotReady:
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' returned an unexpected response: {charging_status}")
            elif self._last_state_change == key.value and key == Hash.GearCommanded:
                try:
                    gear_commanded = GearCommanded(self._vehicle_state.get(Hash.GearCommanded.value))
                except ValueError:
                    _LOGGER.info(f"While in '{self._state.name}', 'GearCommanded' had an unexpected value: {self._vehicle_state.get(Hash.GearCommanded.value)}")
                    continue
                if gear_commanded != GearCommanded.Park:
                    self.change_state(VehicleState.Trip)

    def trip(self) -> None:
        for key in self._get_state_keys():
            if self._last_state_change == key.value and key == Hash.GearCommanded:
                try:
                    gear_commanded = GearCommanded(self._vehicle_state.get(Hash.GearCommanded.value))
                except ValueError:
                    _LOGGER.info(f"While in '{self._state.name}', 'GearCommanded' had an unexpected value: {self._vehicle_state.get(Hash.GearCommanded.value)}")
                    continue
                if gear_commanded == GearCommanded.Park:
                    self.change_state(VehicleState.On)

    def plugged_in(self) -> None:
        for key in self._get_state_keys():
            if self._last_state_change == key.value and key == Hash.ChargingStatus:
                try:
                    charging_status = ChargingStatus(self._vehicle_state.get(Hash.ChargingStatus.value))
                except ValueError:
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' had an unexpected value: {self._vehicle_state.get(Hash.ChargingStatus.value)}")
                    continue
                if charging_status == ChargingStatus.Charging:
                    pass
                elif charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Done:
                    try:
                        key_state = KeyState(self._vehicle_state.get(Hash.KeyState.value))
                    except ValueError:
                        _LOGGER.info(f"While in '{self._state.name}', 'KeyState' had an unexpected value: {self._vehicle_state.get(Hash.KeyState.value)}")
                        continue
                    if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                        self.change_state(VehicleState.Off)
                    elif key_state == KeyState.On or key_state == KeyState.Cranking:
                        self.change_state(VehicleState.On)
                    else:
                        _LOGGER.info(f"While in '{self._state.name}', 'KeyState' returned an unexpected response: {key_state}")
                else:
                    _LOGGER.info(f"While {self._state}, 'ChargingStatus' returned an unexpected response: {charging_status}")
            elif self._last_state_change == key.value and key == Hash.EvseType:
                try:
                    evse_type = EvseType(self._vehicle_state.get(Hash.EvseType.value))
                except ValueError:
                    _LOGGER.info(f"While in '{self._state.name}', 'EvseType' had an unexpected value: {self._vehicle_state.get(Hash.EvseType.value)}")
                    continue
                if evse_type == EvseType.BasAC:
                    self.change_state(VehicleState.AC_Charging)
                elif charging_status != EvseType.NoType:
                    _LOGGER.info(f"While in '{self._state.name}', 'EvseType' returned an unexpected response: {charging_status}")

    def ac_charging(self) -> None:
        for key in self._get_state_keys():
            if self._last_state_change == key.value and key == Hash.ChargingStatus:
                try:
                    charging_status = ChargingStatus(self._vehicle_state.get(Hash.ChargingStatus.value))
                except ValueError:
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' had an unexpected value: {self._vehicle_state.get(Hash.ChargingStatus.value)}")
                    continue
                if charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Done:
                    try:
                        key_state = KeyState(self._vehicle_state.get(Hash.KeyState.value))
                    except ValueError:
                        _LOGGER.info(f"While in '{self._state.name}', 'KeyState' had an unexpected value: {self._vehicle_state.get(Hash.KeyState.value)}")
                        continue
                    if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                        self.change_state(VehicleState.Off)
                    elif key_state == KeyState.On or key_state == KeyState.Cranking:
                        self.change_state(VehicleState.On)
                    else:
                        _LOGGER.info(f"While in '{self._state.name}', 'KeyState' returned an unexpected response: {key_state}")
                else:
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' returned an unexpected response: {charging_status}")
