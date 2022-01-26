"""
State definitions
"""
import logging
from threading import Lock
from queue import PriorityQueue
import json
import time
import datetime

from enum import Enum, unique, auto
from typing import List

from codec_manager import *
from did import KeyState, ChargingStatus, EvseType, GearCommanded, InferredKey
from did import EngineStartRemote, EngineStartNormal, EngineStartDisable, ChargePlugConnected
from state_engine import get_state_value, set_state
from hash import *
from synthetics import update_synthetics

_LOGGER = logging.getLogger('mme')


@unique
class VehicleState(Enum):
        Unknown = auto()            # initial state until another is determined
        Off = auto()                # the vehicle is off
        Accessory = auto()          # the vehicle is on and in Accessory mode
        On = auto()                 # the vehicle is on and in Drivable mode
        Trip = auto()               # the vehicle is in a gear other than Park

        PluggedIn = auto()          # the vehicle has plugged in
        Preconditioning = auto()    # the vehicle is preconditioning (remote start)
        Charging_Starting = auto()  # the vehicle is beginning a charging session
        Charging_AC = auto()        # the vehicle is AC charging
        Charging_DCFC = auto()      # the vehicle is DC fast charging
        Charging_Ended = auto()     # the vehicle is no longer charging


class StateManager:

    _state_file_lookup = {
        VehicleState.Unknown:           {'state_file': 'json/state/unknown.json',           'state_keys': [Hash.InferredKey]},
        VehicleState.Off:               {'state_file': 'json/state/off.json',               'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected]},
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

    def __init__(self) -> None:
        self._state = None
        self._charging_session = None
        self._putback_enabled = False
        self._codec_manager = CodecManager()
        self._command_queue = PriorityQueue()
        self._command_queue_lock = Lock()
        state_functions = {
            VehicleState.Unknown: self.unknown,
            VehicleState.Off: self.off,
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
            starting_time = self._charging_session.get('time')
            ending_time = int(time.time())
            duration_seconds = ending_time - starting_time
            hours, rem = divmod(duration_seconds, 3600)
            minutes, _ = divmod(rem, 60)
            starting_soc = self._charging_session.get(Hash.HvbSOC)
            starting_socd = self._charging_session.get(Hash.HvbSOCDisplayed)
            starting_ete = self._charging_session.get(Hash.HvbEnergyToEmpty)
            starting_charging_input_energy = self._charging_session.get(Hash.ChargerInputEnergy, 0.0)
            latitude = self._charging_session.get(Hash.GpsLatitude, 0.0)
            longitude = self._charging_session.get(Hash.GpsLongitude, 0.0)
            odometer = self._charging_session.get(Hash.LoresOdometer, 0)

            ending_soc = get_state_value(Hash.HvbSOC)
            ending_socd = get_state_value(Hash.HvbSOCDisplayed)
            ending_ete = get_state_value(Hash.HvbEnergyToEmpty)
            ending_charging_input_energy = get_state_value(Hash.ChargerInputEnergy)
            kwh_added = ending_ete - starting_ete
            kwh_used = (ending_charging_input_energy - starting_charging_input_energy) * 0.001
            charging_efficiency = kwh_added / kwh_used if kwh_used > 0 else 0.0
            charging_session = {
                'time':             starting_time,
                'duration':         duration_seconds,
                'location':         {'latitude': latitude, 'longitude': longitude},
                'odometer':         odometer,
                'soc':              {'starting': starting_soc, 'ending': ending_soc},
                'socd':             {'starting': starting_socd, 'ending': ending_socd},
                'ete':              {'starting': starting_ete, 'ending': ending_ete},
                'kwh_added':        kwh_added,
                'kwh_used':         kwh_used,
                'efficiency':       charging_efficiency,
            }
            _LOGGER.info(f"Charging session statistics:")
            _LOGGER.info(f"   session started at {datetime.datetime.fromtimestamp(starting_time).strftime('%Y-%m-%d %H:%M')} for {hours} hours, {minutes} minutes")
            _LOGGER.info(f"   location was ({latitude:.05f},{longitude:.05f}), odometer is {odometer} km")
            _LOGGER.info(f"   starting SOC was {starting_socd}%, ending SOC was {ending_socd}%")
            _LOGGER.info(f"   starting ETE was {starting_ete} kWh, ending ETE was {ending_ete} kWh")
            _LOGGER.info(f"   {kwh_added:.03f} kWh were added, requiring {kwh_used:.03f} kWh from the AC charger")
            _LOGGER.info(f"   overall efficiency is {(charging_efficiency*100):.01f}%")
            self._influxdb.charging_session(charging_session)
            self._charging_session = None

    def _incoming_state(self, state: VehicleState) -> None:
        if state == VehicleState.Charging_Starting:
            self._charging_session = None

    def change_state(self, new_state: VehicleState) -> None:
        if self._state == new_state:
            return
        _LOGGER.info(f"Vehicle state changed from '{self._state.name}' to '{new_state.name}'" if self._state else f"Vehicle state set to '{new_state.name}'")

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
                codec = self._codec_manager.codec(did_id)
                decoded_payload = codec.decode(None, bytearray(state_change.get('payload')))
                arbitration_id = state_change.get('arbitration_id')
                states = decoded_payload.get('states')
                for state in states:
                    for state_name, state_value in state.items():
                        hash = get_hash(f"{arbitration_id:04X}:{did_id:04X}:{state_name}")
                        set_state(hash, state_value)
                        state_data.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': state_name, 'value': state_value})
                        if synthetics := update_synthetics(hash):
                            state_data += synthetics
                return state_data

    def _update_state_machine(self) -> None:
        self._state_function()

    def _get_KeyState(self, key: Hash) -> KeyState:
        key_state = None
        if key == Hash.KeyState:
            try:
                key_state = KeyState(get_state_value(Hash.KeyState))
            except ValueError:
                if key_state := get_state_value(Hash.KeyState):
                    _LOGGER.info(f"While in '{self._state.name}', 'KeyState' had an unexpected value: {key_state}")
        return key_state

    def _get_InferredKey(self, key: Hash) -> InferredKey:
        inferred_key = None
        if key == Hash.InferredKey:
            try:
                inferred_key = InferredKey(get_state_value(Hash.InferredKey))
            except ValueError:
                if inferred_key := get_state_value(Hash.InferredKey):
                    _LOGGER.info(f"While in '{self._state.name}', 'InferredKey' had an unexpected value: {inferred_key}")
        return inferred_key

    def _get_ChargingStatus(self, key: Hash) -> ChargingStatus:
        charging_status = None
        if key == Hash.ChargingStatus:
            try:
                charging_status = ChargingStatus(get_state_value(Hash.ChargingStatus))
            except ValueError:
                if charging_status := get_state_value(Hash.ChargingStatus):
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' had an unexpected value: {charging_status}")
        return charging_status

    def _get_ChargePlugConnected(self, key: Hash) -> ChargePlugConnected:
        charge_plug_connected = None
        if key == Hash.ChargePlugConnected:
            try:
                charge_plug_connected = ChargePlugConnected(get_state_value(Hash.ChargePlugConnected))
            except ValueError:
                if charge_plug_connected := get_state_value(Hash.ChargePlugConnected):
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargePlugConnected' had an unexpected value: {charge_plug_connected}")
        return charge_plug_connected

    def _get_GearCommanded(self, key: Hash) -> GearCommanded:
        gear_commanded = None
        if key == Hash.GearCommanded:
            try:
                gear_commanded = GearCommanded(get_state_value(Hash.GearCommanded))
            except ValueError:
                if gear_commanded := get_state_value(Hash.GearCommanded):
                    _LOGGER.info(f"While in '{self._state.name}', 'GearCommanded' had an unexpected value: {gear_commanded}")
        return gear_commanded

    def _get_EvseType(self, key: Hash) -> EvseType:
        evse_type = None
        if key == Hash.EvseType:
            try:
                evse_type = EvseType(get_state_value(Hash.EvseType))
            except ValueError:
                if evse_type := get_state_value(Hash.EvseType):
                    _LOGGER.info(f"While in '{self._state.name}', 'EvseType' had an unexpected value: {evse_type}")
        return evse_type

    def _get_EngineStartNormal(self, key: Hash) -> EngineStartNormal:
        engine_start_normal = None
        if key == Hash.EngineStartNormal:
            try:
                engine_start_normal = EngineStartNormal(get_state_value(Hash.EngineStartNormal))
            except ValueError:
                if engine_start_normal := get_state_value(Hash.EngineStartNormal):
                    _LOGGER.info(f"While in '{self._state.name}', 'EngineStartNormal' had an unexpected value: {engine_start_normal}")
        return engine_start_normal

    def _get_EngineStartRemote(self, key: Hash) -> EngineStartRemote:
        engine_start_remote = None
        if key == Hash.EngineStartRemote:
            try:
                engine_start_remote = EngineStartRemote(get_state_value(Hash.EngineStartRemote))
            except ValueError:
                if engine_start_remote := get_state_value(Hash.EngineStartRemote):
                    _LOGGER.info(f"While in '{self._state.name}', 'EngineStartRemote' had an unexpected value: {engine_start_remote}")
        return engine_start_remote

    def _get_EngineStartDisable(self, key: Hash) -> EngineStartDisable:
        engine_start_disable = None
        if key == Hash.EngineStartDisable:
            try:
                engine_start_disable = EngineStartDisable(get_state_value(Hash.EngineStartDisable))
            except ValueError:
                if engine_start_disable := get_state_value(Hash.EngineStartDisable):
                    _LOGGER.info(f"While in '{self._state.name}', 'EngineStartDisable' had an unexpected value: {engine_start_disable}")
        return engine_start_disable

    def unknown(self) -> None:
        # 'state_keys': [Hash.InferredKey]},
        for key in self._get_state_keys():
            if inferred_key := self._get_InferredKey(key):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := self._get_EngineStartRemote(Hash.EngineStartRemote):
                        self.change_state(VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off)
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_normal := self._get_EngineStartNormal(Hash.EngineStartNormal):
                        self.change_state(VehicleState.On if engine_start_normal == EngineStartRemote.Yes else VehicleState.Accessory)

    def off(self) -> None:
        # 'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected]},
        for key in self._get_state_keys():
            if inferred_key := self._get_InferredKey(key):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := self._get_EngineStartRemote(Hash.EngineStartRemote):
                        if engine_start_remote == EngineStartRemote.Yes:
                            self.change_state(VehicleState.Preconditioning)
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_normal := self._get_EngineStartNormal(Hash.EngineStartNormal):
                        self.change_state(VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory)
            elif charge_plug_connected := self._get_ChargePlugConnected(key):
                if charge_plug_connected == ChargePlugConnected.Yes:
                    self.change_state(VehicleState.PluggedIn)

    def accessory(self) -> None:
        # 'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected]},
        for key in self._get_state_keys():
            if inferred_key := self._get_InferredKey(key):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := self._get_EngineStartRemote(Hash.EngineStartRemote):
                        self.change_state(VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off)
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_normal := self._get_EngineStartNormal(Hash.EngineStartNormal):
                        self.change_state(VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory)
            elif charge_plug_connected := self._get_ChargePlugConnected(key):
                if charge_plug_connected == ChargePlugConnected.Yes:
                    self.change_state(VehicleState.PluggedIn)

    def on(self) -> None:
        # 'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected, Hash.GearCommanded]},
        for key in self._get_state_keys():
            if inferred_key := self._get_InferredKey(key):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := self._get_EngineStartRemote(Hash.EngineStartRemote):
                        self.change_state(VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off)
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_normal := self._get_EngineStartNormal(Hash.EngineStartNormal):
                        self.change_state(VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory)
            elif charge_plug_connected := self._get_ChargePlugConnected(key):
                if charge_plug_connected == ChargePlugConnected.Yes:
                    self.change_state(VehicleState.PluggedIn)
            elif gear_commanded := self._get_GearCommanded(key):
                if gear_commanded != GearCommanded.Park:
                    self.change_state(VehicleState.Trip)

    def trip(self) -> None:
        # 'state_keys': [Hash.GearCommanded]},
        for key in self._get_state_keys():
            if gear_commanded := self._get_GearCommanded(key):
                if gear_commanded == GearCommanded.Park:
                    if inferred_key := self._get_InferredKey(Hash.InferredKey):
                        if inferred_key == InferredKey.KeyOut:
                            if engine_start_remote := self._get_EngineStartRemote(Hash.EngineStartRemote):
                                self.change_state(VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off)
                        elif inferred_key == InferredKey.KeyIn:
                            if engine_start_normal := self._get_EngineStartNormal(Hash.EngineStartNormal):
                                self.change_state(VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory)

    def preconditioning(self) -> None:
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
            elif remote_start := self._get_EngineStartRemote(key):
                if remote_start == EngineStartRemote.No:
                    self.change_state(VehicleState.Unknown)

    def plugged_in(self) -> None:
        # 'state_keys': [Hash.ChargePlugConnected, Hash.ChargingStatus]},
        for key in self._get_state_keys():
            if charge_plug_connected := self._get_ChargePlugConnected(key):
                if charge_plug_connected == ChargePlugConnected.No:
                    if inferred_key := self._get_InferredKey(Hash.InferredKey):
                        if inferred_key == InferredKey.KeyOut:
                            if engine_start_remote := self._get_EngineStartRemote(Hash.EngineStartRemote):
                                self.change_state(VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off)
                        elif inferred_key == InferredKey.KeyIn:
                            if engine_start_normal := self._get_EngineStartNormal(Hash.EngineStartNormal):
                                self.change_state(VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory)
            elif charging_status := self._get_ChargingStatus(key):
                if charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Wait:
                    pass
                elif charging_status == ChargingStatus.Ready or charging_status == ChargingStatus.Charging:
                    self.change_state(VehicleState.Charging_Starting)
                else:
                    _LOGGER.info(f"While in {self._state}, 'ChargingStatus' returned an unexpected response: {charging_status}")

    def charging_starting(self) -> None:
        if self._charging_session is None:
            self._charging_session = {
                'time': int(time.time()),
            }

        for key in self._get_state_keys():
            if charging_status := self._get_ChargingStatus(key):
                if charging_status == ChargingStatus.Ready or charging_status == ChargingStatus.Wait or charging_status == ChargingStatus.Charging:
                    if self._charging_session.get(Hash.HvbEnergyToEmpty) is None:
                        if hvb_ete := get_state_value(Hash.HvbEnergyToEmpty, None):
                            self._charging_session[Hash.HvbEnergyToEmpty] = hvb_ete ###
                            _LOGGER.debug(f"Saved hvb_ete initial value: {hvb_ete:.03f}")
                    if self._charging_session.get(Hash.HvbSOC) is None:
                        if soc := get_state_value(Hash.HvbSOC, None):
                            self._charging_session[Hash.HvbSOC] = soc
                            _LOGGER.debug(f"Saved soc initial value: {soc:.03f}")
                    if self._charging_session.get(Hash.HvbSOCDisplayed) is None:
                        if soc_displayed := get_state_value(Hash.HvbSOCDisplayed, None):
                            self._charging_session[Hash.HvbSOCDisplayed] = soc_displayed
                            _LOGGER.debug(f"Saved socd initial value: {soc_displayed:.01f}")
                    if self._charging_session.get(Hash.GpsLatitude) is None:
                        if latitude := get_state_value(Hash.GpsLatitude, None):
                            self._charging_session[Hash.GpsLatitude] = latitude
                            _LOGGER.debug(f"Saved latitude initial value: {latitude:.05f}")
                    if self._charging_session.get(Hash.GpsLongitude) is None:
                        if longitude := get_state_value(Hash.GpsLongitude, None):
                            self._charging_session[Hash.GpsLongitude] = longitude
                            _LOGGER.debug(f"Saved longitude initial value: {longitude:.05f}")
                    if self._charging_session.get(Hash.LoresOdometer) is None:
                        if lores_odometer := get_state_value(Hash.LoresOdometer, None):
                            self._charging_session[Hash.LoresOdometer] = lores_odometer
                            _LOGGER.debug(f"Saved lores_odometer initial value: {lores_odometer}")
                    if self._charging_session.get(Hash.ChargerInputEnergy) is None:
                        charger_input_energy = get_state_value(Hash.ChargerInputEnergy, 0.0)
                        set_state(Hash.ChargerInputEnergy, charger_input_energy)
                        self._charging_session[Hash.ChargerInputEnergy] = charger_input_energy
                        _LOGGER.debug(f"Saved charger input energy initial value: {charger_input_energy}")
                    if self._charging_session.get(Hash.ChargerOutputEnergy) is None:
                        charger_output_energy = get_state_value(Hash.ChargerOutputEnergy, 0.0)
                        set_state(Hash.ChargerOutputEnergy, charger_output_energy)
                        self._charging_session[Hash.ChargerOutputEnergy] = charger_output_energy
                        _LOGGER.debug(f"Saved charger output energy initial value: {charger_output_energy}")

                    if charging_status == ChargingStatus.Charging:
                        if evse_type := self._get_EvseType(Hash.EvseType):
                            if evse_type == EvseType.BasAC:
                                self.change_state(VehicleState.Charging_AC)
                            elif evse_type != EvseType.NoType:
                                _LOGGER.error(f"While in '{self._state.name}', 'EvseType' returned an unexpected response: {evse_type}")
                else:
                    _LOGGER.info(f"While in {self._state}, 'ChargingStatus' returned an unexpected response: {charging_status}")

    def charging_ac(self) -> None:
        # 'state_keys': [Hash.ChargingStatus]},
        for key in self._get_state_keys():
            if charging_status := self._get_ChargingStatus(key):
                if charging_status != ChargingStatus.Charging:
                    _LOGGER.debug(f"Charging status changed to: {charging_status}")
                    self.change_state(VehicleState.Charging_Ended)
                else:
                    assert get_state_value(Hash.HvbEnergyToEmpty, None) is not None
                    assert get_state_value(Hash.HvbSOC, None) is not None
                    assert get_state_value(Hash.HvbSOCDisplayed, None) is not None
                    ###assert get_state_value(Hash.GpsLatitude, None) is not None
                    ###assert get_state_value(Hash.GpsLongitude, None) is not None
                    assert get_state_value(Hash.LoresOdometer, None) is not None
                    assert get_state_value(Hash.ChargerInputEnergy, None) is not None
                    assert get_state_value(Hash.ChargerOutputEnergy, None) is not None


    def charging_ended(self) -> None:
        # 'state_keys': [Hash.ChargingStatus]},
        for key in self._get_state_keys():
            if charging_status := self._get_ChargingStatus(key):
                if charging_status != ChargingStatus.Charging:
                    if charge_plug_connected := self._get_ChargePlugConnected(Hash.ChargePlugConnected):
                        if charge_plug_connected == ChargePlugConnected.Yes:
                            self.change_state(VehicleState.PluggedIn)
                        elif inferred_key := self._get_InferredKey(Hash.InferredKey):
                            if inferred_key == InferredKey.KeyOut:
                                if engine_start_remote := self._get_EngineStartRemote(Hash.EngineStartRemote):
                                    self.change_state(VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off)
                            elif inferred_key == InferredKey.KeyIn:
                                if engine_start_normal := self._get_EngineStartNormal(Hash.EngineStartNormal):
                                    self.change_state(VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory)

    def charging_dcfc(self) -> None:
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
