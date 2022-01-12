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


_LOGGER = logging.getLogger('mme')



class StateManager:

    @unique
    class StateDID(Enum):
        KeyState = 0x411F
        EvseType = 0x4851

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
            Charging = 8                # the vehicle has plugged in
            AC_Charging = 9             # the vehicle is AC charging
            DC_Charging = 10            # the vehicle is DC fast charging

    _state_file_lookup = {
        VehicleState.Unknown:           {'state_file': 'json/unknown.json',     'state_keys': ['0716:411F:key_state']},
        VehicleState.Sleeping:          {'state_file': 'json/sleeping.json',    'state_keys': ['0716:411F:key_state', '07E4:484D:charging_status']},
        VehicleState.Off:               {'state_file': 'json/off.json',         'state_keys': ['0716:411F:key_state', '07E4:484D:charging_status']},
        VehicleState.On:                {'state_file': 'json/on.json',          'state_keys': ['0716:411F:key_state', '07E4:484D:charging_status']},
        VehicleState.Charging:          {'state_file': 'json/charging.json',    'state_keys': ['07E4:484D:charging_status', '07E4:4851:evse_type']},
        VehicleState.AC_Charging:       {'state_file': 'json/ac_charging.json', 'state_keys': ['07E4:484D:charging_status']},
        #VehicleState.Trip:              'json/trip.json',
        #VehicleState.Preconditioning:   'json/preconditioning.json',
        #VehicleState.DC_Charging:       'json/dc_charging.json',
    }

    def __init__(self, config: dict) -> None:
        self._config = config
        self._codec_manager = CodecManager(config=self._config)
        self._command_queue = PriorityQueue()

        state_functions = {
            StateManager.VehicleState.Unknown: self.unknown,
            StateManager.VehicleState.Sleeping: self.sleeping,
            StateManager.VehicleState.Off: self.off,
            StateManager.VehicleState.On: self.on,
            StateManager.VehicleState.Charging: self.charging,
            StateManager.VehicleState.AC_Charging: self.ac_charging,
        }
        for k, v in StateManager._state_file_lookup.items():
            v['state_function'] = state_functions.get(k)

        self.change_state(StateManager.VehicleState.Unknown)
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
        self._state_file = StateManager._state_file_lookup.get(
            new_state).get('state_file')
        self._state_function = StateManager._state_file_lookup.get(
            new_state).get('state_function')
        while not self._command_queue.empty():
            self._command_queue.get_nowait()
            self._command_queue.task_done()
        queue_commands = self._load_state_definition(self._state_file)
        self._load_queue(queue_commands)
        _LOGGER.info(f"Vehicle state changed to '{self._state}'")

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
                        self._last_state_change = f"{arbitration_id:04X}:{did_id:04X}:{k}"
                        self._vehicle_state[self._last_state_change] = v
                _LOGGER.debug(self._last_state_change)
                self._state_function()

    def unknown(self) -> None:
        for key in self._get_state_keys():
            if self._last_state_change == key and key == '0716:411F:key_state':
                key_state = self._vehicle_state.get('0716:411F:key_state')
                if key_state == 0 or key_state == 5:
                    self.change_state(StateManager.VehicleState.Off)
                elif key_state == 3:
                    self.change_state(StateManager.VehicleState.On)
                else:
                    _LOGGER.info(f"While {self._state}, 'KeyState' returned an unexpected response: {key_state}")

    def sleeping(self) -> None:
        for key in self._get_state_keys():
            if self._last_state_change == key and key == '0716:411F:key_state':
                key_state = self._vehicle_state.get('0716:411F:key_state')
                if key_state == 0 or key_state == 5:
                    pass
                elif key_state == 3:
                    self.change_state(StateManager.VehicleState.On)
                else:
                    _LOGGER.info(f"While {self._state}, 'KeyState' returned an unexpected response: {key_state}")
            elif self._last_state_change == key and key == '07E4:484D:charging_status':
                charging_status = self._vehicle_state.get('07E4:484D:charging_status')
                if charging_status == 3:
                    self.change_state(StateManager.VehicleState.AC_Charging)
                elif charging_status != 0:
                    _LOGGER.info(f"While {self._state}, 'ChargingStatus' returned an unexpected response: {charging_status}")

    def off(self) -> None:
        for key in self._get_state_keys():
            if self._last_state_change == key and key == '0716:411F:key_state':
                key_state = self._vehicle_state.get('0716:411F:key_state')
                if key_state == 0 or key_state == 5:
                    pass
                elif key_state == 3 or key_state == 4:
                    self.change_state(StateManager.VehicleState.On)
                else:
                    _LOGGER.info(f"While {self._state}, 'KeyState' returned an unexpected response: {key_state}")
            elif self._last_state_change == key and key == '07E4:484D:charging_status':
                charging_status = self._vehicle_state.get('07E4:484D:charging_status')
                if charging_status == 3:
                    self.change_state(StateManager.VehicleState.AC_Charging)
                elif charging_status == 1:
                    pass
                elif charging_status != 0:
                    _LOGGER.info(f"While {self._state}, 'ChargingStatus' returned an unexpected response: {charging_status}")

    def on(self) -> None:
        for key in self._get_state_keys():
            if self._last_state_change == key and key == '0716:411F:key_state':
                key_state = self._vehicle_state.get('0716:411F:key_state')
                if key_state == 0 or key_state == 5:
                    self.change_state(StateManager.VehicleState.Off)
                elif key_state == 3 or key_state == 4:
                    pass
                else:
                    _LOGGER.info(f"While {self._state}, 'KeyState' returned an unexpected response: {key_state}")
            elif self._last_state_change == key and key == '07E4:484D:charging_status':
                charging_status = self._vehicle_state.get('07E4:484D:charging_status')
                if charging_status == 3:
                    self.change_state(StateManager.VehicleState.AC_Charging)
                elif charging_status == 1:
                    pass
                elif charging_status != 0:
                    _LOGGER.info(f"While {self._state}, 'ChargingStatus' returned an unexpected response: {charging_status}")

    def charging(self) -> None:
        for key in self._get_state_keys():
            if self._last_state_change == key and key == '07E4:484D:charging_status':
                charging_status = self._vehicle_state.get('07E4:484D:charging_status')
                if charging_status == 3:
                    pass
                elif charging_status == 0 or charging_status == 4:
                    key_state = self._vehicle_state.get('0716:411F:key_state')
                    if key_state == 0 or key_state == 5:
                        self.change_state(StateManager.VehicleState.Off)
                    elif key_state == 3 or key_state == 4:
                        self.change_state(StateManager.VehicleState.On)
                    else:
                        _LOGGER.info(f"While {self._state}, 'KeyState' returned an unexpected response: {key_state}")
                else:
                    _LOGGER.info(f"While {self._state}, 'ChargingStatus' returned an unexpected response: {charging_status}")
            elif self._last_state_change == key and key == '07E4:4851:evse_type':
                evse_type = self._vehicle_state.get('07E4:4851:evse_type')
                if evse_type == 6:
                    self.change_state(StateManager.VehicleState.AC_Charging)
                elif charging_status != 0:
                    _LOGGER.info(f"While {self._state}, 'EvseType' returned an unexpected response: {charging_status}")

    def ac_charging(self) -> None:
        for key in self._get_state_keys():
            if self._last_state_change == key and key == '07E4:484D:charging_status':
                charging_status = self._vehicle_state.get('07E4:484D:charging_status')
                if charging_status == 0 or charging_status == 4:
                    key_state = self._vehicle_state.get('0716:411F:key_state')
                    if key_state == 0 or key_state == 5:
                        self.change_state(StateManager.VehicleState.Off)
                    elif key_state == 3 or key_state == 4:
                        self.change_state(StateManager.VehicleState.On)
                    else:
                        _LOGGER.info(f"While {self._state}, 'KeyState' returned an unexpected response: {key_state}")
                else:
                    _LOGGER.info(f"While {self._state}, 'ChargingStatus' returned an unexpected response: {charging_status}")
