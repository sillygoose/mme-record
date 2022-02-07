"""
State definitions
"""
import logging
from threading import Lock
from queue import PriorityQueue
import json
import time
import datetime

from typing import List

from codec_manager import *

from hash import *
from synthetics import update_synthetics
from influxdb import influxdb_charging_session
from vehicle_state import VehicleState
from exceptions import RuntimeError

from state_transition import StateTransistion
from state_engine import get_state_value, set_state


_LOGGER = logging.getLogger('mme')


class StateManager(StateTransistion):

    _state_file_lookup = {
        VehicleState.Unknown:           {'state_file': 'json/state/unknown.json',           'state_keys': [Hash.InferredKey]},
        #VehicleState.Unknown:           {'state_file': 'json/other/bcm_coverage.json',           'state_keys': [Hash.InferredKey]},

        VehicleState.Idle:              {'state_file': 'json/state/idle.json',              'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected]},
        VehicleState.Accessory:         {'state_file': 'json/state/accessory.json',         'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected]},
        VehicleState.On:                {'state_file': 'json/state/on.json',                'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected, Hash.GearCommanded]},
        VehicleState.PluggedIn:         {'state_file': 'json/state/pluggedin.json',         'state_keys': [Hash.ChargePlugConnected, Hash.ChargingStatus]},
        VehicleState.Charging_AC:       {'state_file': 'json/state/charging_ac.json',       'state_keys': [Hash.ChargingStatus]},
        VehicleState.Charging_Starting: {'state_file': 'json/state/charging_starting.json', 'state_keys': [Hash.ChargingStatus]},
        VehicleState.Charging_Ended:    {'state_file': 'json/state/charging_ended.json',    'state_keys': [Hash.ChargingStatus]},
        VehicleState.Trip:              {'state_file': 'json/state/trip.json',              'state_keys': [Hash.GearCommanded]},
        ###
        VehicleState.Preconditioning:   {'state_file': 'json/state/preconditioning.json',   'state_keys': [Hash.ChargePlugConnected, Hash.ChargingStatus, Hash.EvseType]},
        VehicleState.Charging_DCFC:     {'state_file': 'json/state/charging_dcfc.json',     'state_keys': [Hash.ChargingStatus, Hash.EvseType]},
    }

    def __init__(self, config) -> None:
        super().__init__(StateManager._state_file_lookup)
        self._vehicle_name = config.vehicle.name
        self._state = None
        self._putback_enabled = False
        self._codec_manager = CodecManager()
        self._command_queue = PriorityQueue()
        self._command_queue_lock = Lock()
        state_functions = {
            VehicleState.Unknown: self.unknown,
            VehicleState.Idle: self.idle,
            VehicleState.Accessory: self.accessory,
            VehicleState.On: self.on,
            VehicleState.Trip: self.trip,
            VehicleState.Preconditioning: self.preconditioning,
            VehicleState.PluggedIn: self.plugged_in,
            VehicleState.Charging_AC: self.charging_ac,
            VehicleState.Charging_DCFC: self.charging_dcfc,
            VehicleState.Charging_Starting: self.charging_starting,
            VehicleState.Charging_Ended: self.charging_ended,
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

    def _outgoing_state(self, state: VehicleState) -> None:
        if state == VehicleState.Charging_Ended:
            charger_type = self._charging_session.get('type')
            starting_time = self._charging_session.get('time')
            ending_time = int(time.time())
            duration_seconds = ending_time - starting_time
            starting_soc = self._charging_session.get(Hash.HvbSoC)
            starting_socd = self._charging_session.get(Hash.HvbSoCD)
            starting_ete = self._charging_session.get(Hash.HvbEtE)
            starting_charging_input_energy = self._charging_session.get(Hash.ChargerInputEnergy, 0.0)
            starting_lvb_energy = self._charging_session.get(Hash.LvbEnergy)
            latitude = self._charging_session.get(Hash.GpsLatitude, 0.0)
            longitude = self._charging_session.get(Hash.GpsLongitude, 0.0)
            odometer = self._charging_session.get(Hash.LoresOdometer, 0)

            ending_soc = get_state_value(Hash.HvbSoC)
            ending_socd = get_state_value(Hash.HvbSoCD)
            ending_ete = get_state_value(Hash.HvbEtE)
            ending_charging_input_energy = get_state_value(Hash.ChargerInputEnergy)
            ending_lvb_energy = get_state_value(Hash.LvbEnergy)
            delta_lvb_energy = ending_lvb_energy - starting_lvb_energy
            delta_hvb_energy = ending_ete - starting_ete
            wh_added = delta_hvb_energy + delta_lvb_energy
            wh_used = ending_charging_input_energy - starting_charging_input_energy
            charging_efficiency = wh_added / wh_used if wh_used > 0 else 0.0
            max_input_power = get_state_value(Hash.ChargerInputPowerMax)
            session_datetime = datetime.datetime.fromtimestamp(starting_time).strftime('%Y-%m-%d %H:%M')
            hours, rem = divmod(duration_seconds, 3600)
            minutes, _ = divmod(rem, 60)
            charging_session = {
                'type':             charger_type,
                'time':             starting_time,
                'duration':         duration_seconds,
                'location':         {'latitude': latitude, 'longitude': longitude},
                'odometer':         odometer,
                'soc':              {'starting': starting_soc, 'ending': ending_soc},
                'socd':             {'starting': starting_socd, 'ending': ending_socd},
                'ete':              {'starting': starting_ete, 'ending': ending_ete},
                'kwh_added':        wh_added * 0.001,
                'kwh_used':         wh_used * 0.001,
                'efficiency':       charging_efficiency,
                'max_power':        max_input_power,
            }
            _LOGGER.info(f"Charging session statistics:")
            _LOGGER.info(f"   {charger_type} charging session started at {session_datetime} for {hours} hours, {minutes} minutes")
            _LOGGER.info(f"   location was ({latitude:.05f},{longitude:.05f}), odometer is {odometer} km")
            _LOGGER.info(f"   starting SoC was {starting_socd:.01f}%, ending SoC was {ending_socd:.01f}%")
            _LOGGER.info(f"   starting EtE was {starting_ete:.0f} Wh, ending EtE was {ending_ete:.0f} Wh, LVB delta energy was {delta_lvb_energy:.0f} Wh")
            _LOGGER.info(f"   {wh_added:.0f} Wh were added, requiring {wh_used:.0f} Wh from the AC charger")
            _LOGGER.info(f"   overall efficiency is {(charging_efficiency*100):.01f}%")
            _LOGGER.info(f"   maximum input power {max_input_power:.0f} W")
            influxdb_charging_session(session=charging_session, vehicle=self._vehicle_name)
            self._charging_session = None

    def _incoming_state(self, state: VehicleState) -> None:
        if state == VehicleState.Charging_Starting:
            self._charging_session = None

    def change_state(self, new_state: VehicleState) -> None:
        if self._state == new_state or new_state == VehicleState.Unchanged:
            return
        _LOGGER.info(f"'{self._vehicle_name}' state changed from '{self._state.name}' to '{new_state.name}'" if self._state else f"'{self._vehicle_name}' state set to '{new_state.name}'")

        self._putback_enabled = False
        self._flush_queue()

        self._outgoing_state(self._state)
        self._state = new_state
        self._state_time = time.time()
        self._state_file = StateManager._state_file_lookup.get(new_state).get('state_file')
        self._state_function = StateManager._state_file_lookup.get(new_state).get('state_function')
        self._queue_commands = self._load_state_definition(self._state_file)
        self._incoming_state(self._state)

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

    def _get_state_keys(self) -> List[str]:
        return StateManager._state_file_lookup.get(self._state).get('state_keys')

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
        if new_state := self._state_function():
            self.change_state(new_state)
