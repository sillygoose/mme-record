"""
State definitions
"""
import logging
from threading import Lock
from queue import PriorityQueue
import json
import time

from typing import List
from config.configuration import Configuration

from codec_manager import *

from hash import *
from synthetics import update_synthetics
from vehicle_state import CallType, VehicleState
from exceptions import RuntimeError

from state_transition import StateTransistion
from state_engine import set_state


_LOGGER = logging.getLogger('mme')


class StateManager(StateTransistion):

    _state_file_lookup = {
        VehicleState.Unknown:           {'state_file': 'json/state/unknown.json',           'state_keys': [Hash.InferredKey]},
        VehicleState.Idle:              {'state_file': 'json/state/idle.json',              'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected]},

        VehicleState.Accessory:         {'state_file': 'json/state/accessory.json',         'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected]},
        VehicleState.On:                {'state_file': 'json/state/on.json',                'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected, Hash.GearCommanded]},

        VehicleState.PluggedIn:         {'state_file': 'json/state/pluggedin.json',         'state_keys': [Hash.ChargePlugConnected, Hash.ChargingStatus]},
        VehicleState.Charging_AC:       {'state_file': 'json/state/charging_ac.json',       'state_keys': [Hash.ChargingStatus]},
        VehicleState.Charging_Starting: {'state_file': 'json/state/charging_starting.json', 'state_keys': [Hash.ChargingStatus]},
        VehicleState.Charging_Ended:    {'state_file': 'json/state/charging_ended.json',    'state_keys': [Hash.ChargingStatus]},

        VehicleState.Trip_Starting:     {'state_file': 'json/state/trip_starting.json',     'state_keys': [Hash.GearCommanded]},
        VehicleState.Trip:              {'state_file': 'json/state/trip.json',              'state_keys': [Hash.GearCommanded]},
        VehicleState.Trip_Ending:       {'state_file': 'json/state/trip_ending.json',       'state_keys': [Hash.GearCommanded]},

        ###
        VehicleState.Preconditioning:   {'state_file': 'json/state/preconditioning.json',   'state_keys': [Hash.ChargePlugConnected, Hash.ChargingStatus, Hash.EvseType]},
        VehicleState.Charging_DCFC:     {'state_file': 'json/state/charging_dcfc.json',     'state_keys': [Hash.ChargingStatus, Hash.EvseType]},
    }

    def __init__(self, config: Configuration) -> None:
        super().__init__(config)
        self._config = dict(config.record)
        self._state = None
        self._state_function = None
        self._putback_enabled = False
        self._codec_manager = CodecManager(config)
        self._command_queue = PriorityQueue()
        self._command_queue_lock = Lock()
        state_functions = {
            VehicleState.Unknown:               self.unknown,
            VehicleState.Idle:                  self.idle,
            VehicleState.Accessory:             self.accessory,
            VehicleState.On:                    self.on,
            VehicleState.Trip_Starting:         self.trip_starting,
            VehicleState.Trip:                  self.trip,
            VehicleState.Trip_Ending:           self.trip_ending,
            VehicleState.Preconditioning:       self.preconditioning,
            VehicleState.PluggedIn:             self.plugged_in,
            VehicleState.Charging_AC:           self.charging_ac,
            VehicleState.Charging_DCFC:         self.charging_dcfc,
            VehicleState.Charging_Starting:     self.charging_starting,
            VehicleState.Charging_Ended:        self.charging_ended,
        }
        assert len(state_functions) == len(StateManager._state_file_lookup)
        for k, v in StateManager._state_file_lookup.items():
            v['state_function'] = state_functions.get(k)

    def start(self) -> None:
        self.change_state(VehicleState.Unknown)

    def stop(self) -> None:
        pass

    def current_state(self) -> VehicleState:
        return self._state

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

    def change_state(self, new_state: VehicleState) -> None:
        if self._state == new_state or new_state == VehicleState.Unchanged:
            return
        if self._state is None:
            _LOGGER.info(f"'{self._vehicle_name}' state set to '{new_state.name}'")
        else:
            _LOGGER.info(f"'{self._vehicle_name}' state changed from '{self._state.name}' to '{new_state.name}'")

        self._putback_enabled = False
        self._flush_queue()

        if state_keys := self._get_state_keys(self._state):
            self._state_function(state_keys=state_keys, call_type = CallType.Outgoing)
        self._state = new_state
        self._state_time = time.time()
        self._state_function = self._get_state_function(new_state)
        self._state_file = self._get_state_file(new_state)
        self._queue_commands = self._load_state_definition(self._state_file)
        state_keys = self._get_state_keys(self._state)
        self._state_function(state_keys=state_keys, call_type = CallType.Incoming)

    def _flush_queue(self) -> None:
        with self._command_queue_lock:
            while not self._command_queue.empty():
                self._command_queue.get_nowait()

    def _load_queue(self) -> None:
        with self._command_queue_lock:
            while not self._command_queue.empty():
                self._command_queue.get_nowait()
            for module in self._queue_commands:
                enable = module.get('enable', True)
                if enable:
                    period = module.get('period', 5)
                    offset = module.get('offset', 0)
                    payload = (time.time() + offset, period, [module])
                    self._command_queue.put(payload)
            self._putback_enabled = True

    def _get_state_keys(self, state: VehicleState) -> List[str]:
        if state is None:
            return None
        return StateManager._state_file_lookup.get(state).get('state_keys')

    def _get_state_file(self, state) -> List[str]:
        return StateManager._state_file_lookup.get(state).get('state_file')

    def _get_state_function(self, state) -> List[str]:
        return StateManager._state_file_lookup.get(state).get('state_function')

    def update_vehicle_state(self, state_change: dict) -> List[dict]:
        state_data = []
        if state_change.get('type', None) is None:
            if did_id := state_change.get('did_id', None):
                arbitration_id = state_change.get('arbitration_id')
                if codec := self._codec_manager.codec(did_id):
                    decoded_payload = codec.decode(None, bytearray(state_change.get('payload')))
                    states = decoded_payload.get('states')
                    for state in states:
                        for state_name, state_value in state.items():
                            if hash := get_hash(f"{arbitration_id:04X}:{did_id:04X}:{state_name}"):
                                set_state(hash, state_value)
                                state_data.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': state_name, 'value': state_value})
                                if synthetics := update_synthetics(hash):
                                    state_data += synthetics
                return state_data

    def _update_state_machine(self) -> None:
        state_keys = self._get_state_keys(self._state)
        if new_state := self._state_function(state_keys=state_keys):
            self.change_state(new_state)
