"""
State definitions
"""

import logging
from operator import truediv
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
from state_engine import set_state, get_state_value


_LOGGER = logging.getLogger('mme')


class StateManager(StateTransistion):

    _state_file_lookup = {
        VehicleState.Unknown:           {'state_file': 'json/state/unknown.json'},
        VehicleState.Idle:              {'state_file': 'json/state/idle.json'},

        VehicleState.Accessory:         {'state_file': 'json/state/accessory.json'},
        VehicleState.On:                {'state_file': 'json/state/on.json'},

        VehicleState.PluggedIn:         {'state_file': 'json/state/pluggedin.json'},
        VehicleState.Preconditioning:   {'state_file': 'json/state/preconditioning.json'},

        VehicleState.Trip_Starting:     {'state_file': 'json/state/trip_starting.json'},
        VehicleState.Trip:              {'state_file': 'json/state/trip.json'},
        VehicleState.Trip_Ending:       {'state_file': 'json/state/trip_ending.json'},

        VehicleState.Charge_Starting:   {'state_file': 'json/state/charge_starting.json'},
        VehicleState.Charge_AC:         {'state_file': 'json/state/charge_ac.json'},
        VehicleState.Charge_DCFC:       {'state_file': 'json/state/charge_dcfc.json'},
        VehicleState.Charge_Ending:     {'state_file': 'json/state/charge_ending.json'},
    }

    def __init__(self, config: Configuration) -> None:
        super().__init__()
        ###self._vehicle_name = config.vehicle.name
        ###self._vehicle_hash = hash(config.vehicle.vin)
        self._state = None
        self._state_function = self.dummy
        self._putback_enabled = False
        self._codec_manager = CodecManager(config.record)
        self._command_queue = PriorityQueue()
        self._command_queue_lock = Lock()
        record_options = dict(config.record)
        self._minimum_trip = record_options.get('trip_minimum', 0.1)
        self._minimum_charge = record_options.get('charge_minimum', 0)
        state_functions = {
            VehicleState.Unknown:               self.unknown,
            VehicleState.Idle:                  self.idle,
            VehicleState.Accessory:             self.accessory,
            VehicleState.On:                    self.on,

            VehicleState.Trip_Starting:         self.trip_starting,
            VehicleState.Trip:                  self.trip,
            VehicleState.Trip_Ending:           self.trip_ending,

            VehicleState.PluggedIn:             self.plugged_in,
            VehicleState.Preconditioning:       self.preconditioning,
            VehicleState.PluggedIn:             self.plugged_in,

            VehicleState.Charge_Starting:       self.charge_starting,
            VehicleState.Charge_AC:             self.charge_ac,
            VehicleState.Charge_DCFC:           self.charge_dcfc,
            VehicleState.Charge_Ending:         self.charge_ending,
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

    def command_queue_empty(self) -> bool:
        return self._command_queue.empty()

    def _load_state_definition(self, file: str) -> List[dict]:
        with open(file) as infile:
            try:
                state_definition = json.load(infile)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"JSON error in '{file}' at line {e.lineno}")
            except FileNotFoundError as e:
                raise RuntimeError(f"{e}")

        _LOGGER.debug(f"Loading state file '{file}'")
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

        self._state_function(call_type = CallType.Outgoing)

        if self._state is None:
            _LOGGER.info(f"Initial state set to '{new_state.name}'")
        else:
            _LOGGER.info(f"{get_state_value(Hash.VehicleID)} state changed from '{self._state.name}' to '{new_state.name}'")

        self._state = new_state
        self._state_time = time.time()
        self._state_function = self._get_state_function(new_state)
        self._state_file = self._get_state_file(new_state)
        self._queue_commands = self._load_state_definition(self._state_file)
        self._load_queue()
        self._state_function(call_type = CallType.Incoming)

    def _load_queue(self) -> None:
        with self._command_queue_lock:
            self._putback_enabled = False
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

    def _get_state_file(self, state) -> List[str]:
        return StateManager._state_file_lookup.get(state).get('state_file')

    def _get_state_function(self, state) -> List[str]:
        return StateManager._state_file_lookup.get(state).get('state_function')

    def _saved_hash(self, hash) -> bool:
        trip_saved_hashes = [
            Hash.HiresSpeed,
            Hash.HiresOdometer,
            Hash.GpsLatitude,
            Hash.GpsLongitude,
            Hash.GpsElevation,
            Hash.HvbSoC,
            Hash.HvbEtE,
            Hash.HvbTemp,
            Hash.ExteriorTemperature,
            Hash.InteriorTemperature,
        ]
        ac_charge_saved_hashes = [
            Hash.HvbVoltage,
            Hash.HvbCurrent,
            Hash.HvbSoC,
            Hash.HvbEtE,
            Hash.HvbTemp,
            Hash.ExteriorTemperature,
            Hash.InteriorTemperature,
        ]
        if self._state == VehicleState.Trip:
            if hash in trip_saved_hashes:
                return True
        if self._state == VehicleState.Charge_AC:
            if hash in ac_charge_saved_hashes:
                return True
        return False

    def update_vehicle_state(self, state_change: dict) -> List[dict]:
        state_data = []
        if state_change.get('type', None) is None:
            if did_id := state_change.get('did_id', None):
                arbitration_id = state_change.get('arbitration_id')
                payload = state_change.get('payload')
                states = payload.get('states')
                for state in states:
                    for state_name, state_value in state.items():
                        if hash := get_hash(f"{arbitration_id:04X}:{did_id:04X}:{state_name}"):
                            set_state(hash, state_value)
                            update_synthetics(hash)
                            if self._saved_hash(hash):
                                state_data.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': state_name, 'value': state_value})
            return state_data

    def _update_state_machine(self) -> None:
        if new_state := self._state_function(call_type = CallType.Default):
            self.change_state(new_state)
