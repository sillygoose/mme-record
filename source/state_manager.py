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
            AC_Charging = 8             # the vehicle is AC charging (Level 1 or Level 2)
            DC_Charging = 9             # the vehicle is DC fast charging

    _state_file_lookup = {
        VehicleState.Unknown:           {'state_file': 'json/unknown.json', 'state_function': None},
        VehicleState.Sleeping:          {'state_file': 'json/sleeping.json', 'state_function': None},
        VehicleState.Off:               {'state_file': 'json/off.json', 'state_function': None},
        VehicleState.On:                {'state_file': 'json/on.json', 'state_function': None},
        #VehicleState.Trip:              'json/trip.json',
        #VehicleState.Preconditioning:   'json/preconditioning.json',
        VehicleState.AC_Charging:       {'state_file': 'json/ac_charging.json', 'state_function': None},
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
        _LOGGER.info(f"Changed vehicle state to 'something'")

    def unknown(self, state_change: dict) -> None:
        if state_change.get('type', None) is None:
            did_id = state_change.get('did_id', None)
            if did_id:
                codec = self._codec_manager.codec(did_id)
                decoded_playload = codec.decode(None, bytearray(state_change.get('payload')))
                states = decoded_playload.get('states')
                if StateManager.StateDID(did_id) == StateManager.StateDID.KeyState:
                    self._vehicle_state[StateManager.StateDID(did_id)] = states[0].get('key_state', None)
                    if self._vehicle_state[StateManager.StateDID(did_id)] == 5:
                        self.change_state(StateManager.VehicleState.Sleeping)
                    elif self._vehicle_state[StateManager.StateDID(did_id)] == 3:
                        self.change_state(StateManager.VehicleState.On)
                    else:
                        _LOGGER.info(
                            f"KeyState returned an unexpected response: {self._vehicle_state[StateManager.StateDID(did_id)]}")

        else:
            _LOGGER.info(
                f"Vehicle returned an unexpected response: {state_change}")

    def sleeping(self, state_change: dict) -> None:
        if state_change.get('type', None) is None:
            did_id = state_change.get('did_id', None)
            if did_id:
                codec = self._codec_manager.codec(did_id)
                decoded_playload = codec.decode(
                    None, bytearray(state_change.get('payload')))
                states = decoded_playload.get('states')
                if StateManager.StateDID(did_id) == StateManager.StateDID.KeyState:
                    self._vehicle_state[StateManager.StateDID(
                        did_id)] = states[0].get('key_state', None)
                    if self._vehicle_state[StateManager.StateDID(did_id)] == 3:
                        self.change_state(StateManager.VehicleState.On)
                elif StateManager.StateDID(did_id) == StateManager.StateDID.EvseType:
                    self._vehicle_state[StateManager.StateDID(
                        did_id)] = states[0].get('evse_type', None)
                    if self._vehicle_state[StateManager.StateDID(did_id)] == 6:
                        self.change_state(StateManager.VehicleState.AC_Charging)
        else:
            _LOGGER.info(
                f"Vehicle returned an unexpected response: {state_change}")

    def off(self, state_change: dict) -> None:
        if state_change.get('type', None) is None:
            did_id = state_change.get('did_id', None)
        else:
            _LOGGER.info(
                f"Vehicle returned an unexpected response: {state_change}")

    def on(self, state_change: dict) -> None:
        if state_change.get('type', None) is None:
            did_id = state_change.get('did_id', None)
        else:
            _LOGGER.info(
                f"Vehicle returned an unexpected response: {state_change}")

    def ac_charging(self, state_change: dict) -> None:
        if state_change.get('type', None) is None:
            did_id = state_change.get('did_id', None)
        else:
            _LOGGER.info(
                f"Vehicle returned an unexpected response: {state_change}")
