"""
State definitions
"""
import logging
from threading import Lock
from queue import PriorityQueue
import json
import time

from enum import Enum, unique, auto
from typing import List, Tuple

from codec_manager import *
from did import KeyState, ChargingStatus, EvseType, GearCommanded, InferredKey
from did import EngineStartRemote, EngineStartNormal, EngineStartDisable, ChargePlugConnected


_LOGGER = logging.getLogger('mme')


@unique
class VehicleState(Enum):
        Unknown = auto()            # initial state until another is determined
        Off = auto()                # the vehicle is off
        Accessory = auto()          # the vehicle is on in Accessory mode
        On = auto()                 # the vehicle is on in Drivable mode
        Trip = auto()               # the vehicle is in a gear other than Park
        Preconditioning = auto()    # the vehicle is preconditioning (remote start)
        PluggedIn = auto()          # the vehicle has plugged in
        Charging_AC = auto()        # the vehicle is AC charging
        Charging_DCFC = auto()      # the vehicle is DC fast charging
        Charging_Starting = auto()  # the vehicle is beginning a charging session
        Charging_Ended = auto()     # the vehicle is no longer charging


@unique
class Hash(Enum):
    KeyState                = '0716:411F:key_state'
    InferredKey             = '0726:417D:inferred_key'
    EvseType                = '07E4:4851:evse_type'
    ChargingStatus          = '07E4:484D:charging_status'
    GearCommanded           = '07E2:1E12:gear_commanded'
    ChargePlugConnected     = '07E2:4843:charge_plug_connected'

    HvbSOC                  = '07E4:4801:hvb_soc'
    HvbSOCDisplayed         = '07E4:4845:hvb_soc_displayed'
    HvbEnergyToEmpty        = '07E4:4848:hvb_ete'
    GpsLatitude             = '07D0:8012:gps_latitude'
    GpsLongitude            = '07D0:8012:gps_longitude'
    HiresOdometer           = '0720:404C:hires_odometer'

    EngineStartNormal       = '0726:41B9:engine_start_normal'
    EngineStartDisable      = '0726:41B9:engine_start_disable'
    EngineStartRemote       = '0726:41B9:engine_start_remote'

    HvbVoltage              = '07E4:480D:hvb_voltage'
    HvbCurrent              = '07E4:48F9:hvb_current'
    HvbPower                = 'FFFF:8000:hvb_power'

    LvbVoltage              = '0726:402A:lvb_voltage'
    LvbCurrent              = '0726:402B:lvb_current'
    LvbPower                = 'FFFF:8001:lvb_power'

    ChargerInputVoltage     = '07E2:485E:charger_input_voltage'
    ChargerInputCurrent     = '07E2:485F:charger_input_current'
    ChargerInputPower       = 'FFFF:8002:charger_input_power'

    ChargerOutputVoltage    = '07E2:484A:charger_output_voltage'
    ChargerOutputCurrent    = '07E2:4850:charger_output_current'
    ChargerOutputPower      = 'FFFF:8003:charger_output_power'


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
        self._vehicle_state = {}
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
            #hours, rem = divmod(duration_seconds, 3600)
            #minutes, _ = divmod(rem, 60)
            starting_soc = self._charging_session.get(Hash.HvbSOC.value)
            starting_socd = self._charging_session.get(Hash.HvbSOCDisplayed.value)
            starting_ete = self._charging_session.get(Hash.HvbEnergyToEmpty.value)
            latitude = self._charging_session.get(Hash.GpsLatitude.value)
            longitude = self._charging_session.get(Hash.GpsLongitude.value)
            odometer = self._charging_session.get(Hash.HiresOdometer.value)

            ending_soc = self._vehicle_state.get(Hash.HvbSOC.value)
            ending_socd = self._vehicle_state.get(Hash.HvbSOCDisplayed.value)
            ending_ete = self._vehicle_state.get(Hash.HvbEnergyToEmpty.value)
            kwh_added = ending_ete - starting_ete
            charging_session = {
                'time':             starting_time,
                #'start':            time.strftime('%Y-%m-%d %H:%M', time.localtime(starting_time)),
                'duration':         duration_seconds,
                'location':         {'latitude': latitude, 'longitude': longitude},
                'odometer':         odometer,
                'soc':              {'starting': starting_soc, 'ending': ending_soc},
                'socd':             {'starting': starting_socd, 'ending': ending_socd},
                'ete':              {'starting': starting_ete, 'ending': ending_ete},
                'kwh_added':        kwh_added,
            }
            _LOGGER.info(f"Charging session: {charging_session}")
            self._influxdb.charging_session(charging_session)
            self._charging_session = None

    def _incoming_state(self, state: VehicleState) -> None:
        if state == VehicleState.Charging_Starting:
            self._charging_session = None

    def change_state(self, new_state: VehicleState) -> None:
        if self._state == new_state:
            return
        _LOGGER.info(f"Vehicle state changed from '{self._state.name}' to '{new_state.name}'" if self._state else f"Vehicle state set to '{new_state.name}'")

        self._outgoing_state(self._state)
        self._state = new_state
        self._state_time = time.time()
        self._state_file = StateManager._state_file_lookup.get(new_state).get('state_file')
        self._state_function = StateManager._state_file_lookup.get(new_state).get('state_function')
        self._queue_commands = self._load_state_definition(self._state_file)
        self._putback_enabled = False
        self._incoming_state(self._state)

    def _load_queue(self) -> None:
        with self._command_queue_lock:
            while not self._command_queue.empty():
                self._command_queue.get_nowait()
            for module in self._queue_commands:
                enable = module.get('enable', True)
                if enable:
                    period = module.get('period', 5)
                    payload = (time.time(), period, [module])
                    self._command_queue.put(payload)
            self._putback_enabled = True

    def _get_state_keys(self) -> List[str]:
        return StateManager._state_file_lookup.get(self._state).get('state_keys')

    def _hash_fields(self, hash: Hash) -> Tuple[int, int, str]:
        hash_fields = hash.value.split(':')
        return int(hash_fields[0], base=16), int(hash_fields[1], base=16), hash_fields[2]

    def _calculate_synthetic(self, hash: str) -> dict:
        synthetic = None
        try:
            if synthetic_hash := StateManager._synthetic_hashes.get(Hash(hash), None):
                if synthetic_hash == Hash.HvbPower:
                    hvb_power = self._vehicle_state.get(Hash.HvbVoltage.value, 0.0) * self._vehicle_state.get(Hash.HvbCurrent.value, 0.0)
                    self._vehicle_state[Hash.HvbPower.value] = hvb_power
                    arbitration_id, did_id, synthetic_name = self._hash_fields(Hash.HvbPower)
                    synthetic = {'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': hvb_power}
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: HVB power is {hvb_power:.0f} W (calculated)")
                elif synthetic_hash == Hash.LvbPower:
                    lvb_power = self._vehicle_state.get(Hash.LvbVoltage.value, 0.0) * self._vehicle_state.get(Hash.LvbCurrent.value, 0.0)
                    self._vehicle_state[Hash.LvbPower.value] = lvb_power
                    arbitration_id, did_id, synthetic_name = self._hash_fields(Hash.LvbPower)
                    synthetic = {'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': lvb_power}
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: LVB power is {lvb_power:.0f} W (calculated)")
                elif synthetic_hash == Hash.ChargerInputPower:
                    charger_input_power = self._vehicle_state.get(Hash.ChargerInputVoltage.value, 0.0) * self._vehicle_state.get(Hash.ChargerInputCurrent.value, 0.0)
                    self._vehicle_state[Hash.ChargerInputPower.value] = charger_input_power
                    arbitration_id, did_id, synthetic_name = self._hash_fields(Hash.ChargerInputPower)
                    synthetic = {'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': charger_input_power}
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger input power is {charger_input_power:.0f} W (calculated)")
                elif synthetic_hash == Hash.ChargerOutputPower:
                    charger_output_power = self._vehicle_state.get(Hash.ChargerOutputVoltage.value, 0.0) * self._vehicle_state.get(Hash.ChargerOutputCurrent.value, 0.0)
                    self._vehicle_state[Hash.ChargerOutputPower.value] = charger_output_power
                    arbitration_id, did_id, synthetic_name = self._hash_fields(Hash.ChargerOutputPower)
                    synthetic = {'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': charger_output_power}
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger output power is {charger_output_power:.0f} W (calculated)")
        except ValueError:
            pass
        return synthetic

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
                        hash = f"{arbitration_id:04X}:{did_id:04X}:{state_name}"
                        self._last_state_change = hash
                        self._vehicle_state[hash] = state_value
                        state_data.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': state_name, 'value': state_value})
                        if synthetic := self._calculate_synthetic(hash):
                            state_data.append(synthetic)
                        self._state_function()
                return state_data

    def _get_KeyState(self, key: Hash) -> KeyState:
        key_state = None
        if key == Hash.KeyState:
            try:
                key_state = KeyState(self._vehicle_state.get(Hash.KeyState.value))
            except ValueError:
                if self._vehicle_state.get(Hash.KeyState.value):
                    _LOGGER.info(f"While in '{self._state.name}', 'KeyState' had an unexpected value: {self._vehicle_state.get(Hash.KeyState.value)}")
        return key_state

    def _get_InferredKey(self, key: Hash) -> InferredKey:
        inferred_key = None
        if key == Hash.InferredKey:
            try:
                inferred_key = InferredKey(self._vehicle_state.get(Hash.InferredKey.value))
            except ValueError:
                if self._vehicle_state.get(Hash.InferredKey.value):
                    _LOGGER.info(f"While in '{self._state.name}', 'InferredKey' had an unexpected value: {self._vehicle_state.get(Hash.InferredKey.value)}")
        return inferred_key

    def _get_ChargingStatus(self, key: Hash) -> ChargingStatus:
        charging_status = None
        if key == Hash.ChargingStatus:
            try:
                charging_status = ChargingStatus(self._vehicle_state.get(Hash.ChargingStatus.value))
            except ValueError:
                if self._vehicle_state.get(Hash.ChargingStatus.value):
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' had an unexpected value: {self._vehicle_state.get(Hash.ChargingStatus.value)}")
        return charging_status

    def _get_ChargePlugConnected(self, key: Hash) -> ChargePlugConnected:
        charge_plug_connected = None
        if key == Hash.ChargePlugConnected:
            try:
                charge_plug_connected = ChargePlugConnected(self._vehicle_state.get(Hash.ChargePlugConnected.value))
            except ValueError:
                if self._vehicle_state.get(Hash.ChargePlugConnected.value):
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargePlugConnected' had an unexpected value: {self._vehicle_state.get(Hash.ChargePlugConnected.value)}")
        return charge_plug_connected

    def _get_GearCommanded(self, key: Hash) -> GearCommanded:
        gear_commanded = None
        if key == Hash.GearCommanded:
            try:
                gear_commanded = GearCommanded(self._vehicle_state.get(Hash.GearCommanded.value))
            except ValueError:
                if self._vehicle_state.get(Hash.GearCommanded.value):
                    _LOGGER.info(f"While in '{self._state.name}', 'GearCommanded' had an unexpected value: {self._vehicle_state.get(Hash.GearCommanded.value)}")
        return gear_commanded

    def _get_EvseType(self, key: Hash) -> EvseType:
        evse_type = None
        if key == Hash.EvseType:
            try:
                evse_type = EvseType(self._vehicle_state.get(Hash.EvseType.value))
            except ValueError:
                if self._vehicle_state.get(Hash.EvseType.value):
                    _LOGGER.info(f"While in '{self._state.name}', 'EvseType' had an unexpected value: {self._vehicle_state.get(Hash.EvseType.value)}")
        return evse_type

    def _get_EngineStartNormal(self, key: Hash) -> EngineStartNormal:
        engine_start_normal = None
        if key == Hash.EngineStartNormal:
            try:
                engine_start_normal = EngineStartNormal(self._vehicle_state.get(Hash.EngineStartNormal.value))
            except ValueError:
                if self._vehicle_state.get(Hash.EngineStartNormal.value):
                    _LOGGER.info(f"While in '{self._state.name}', 'EngineStartNormal' had an unexpected value: {self._vehicle_state.get(Hash.EngineStartNormal.value)}")
        return engine_start_normal

    def _get_EngineStartRemote(self, key: Hash) -> EngineStartRemote:
        engine_start_remote = None
        if key == Hash.EngineStartRemote:
            try:
                engine_start_remote = EngineStartRemote(self._vehicle_state.get(Hash.EngineStartRemote.value))
            except ValueError:
                if self._vehicle_state.get(Hash.EngineStartRemote.value):
                    _LOGGER.info(f"While in '{self._state.name}', 'EngineStartRemote' had an unexpected value: {self._vehicle_state.get(Hash.EngineStartRemote.value)}")
        return engine_start_remote

    def _get_EngineStartDisable(self, key: Hash) -> EngineStartDisable:
        engine_start_disable = None
        if key == Hash.EngineStartDisable:
            try:
                engine_start_disable = EngineStartDisable(self._vehicle_state.get(Hash.EngineStartDisable.value))
            except ValueError:
                if self._vehicle_state.get(Hash.EngineStartDisable.value):
                    _LOGGER.info(f"While in '{self._state.name}', 'EngineStartDisable' had an unexpected value: {self._vehicle_state.get(Hash.EngineStartDisable.value)}")
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
                if charging_status == ChargingStatus.NotReady:
                    pass
                elif charging_status == ChargingStatus.Charging:
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
                if charging_status == ChargingStatus.Wait:
                    pass
                elif charging_status == ChargingStatus.Charging:
                    if self._charging_session.get(Hash.HvbEnergyToEmpty.value) is None:
                        if hvb_ete := self._vehicle_state.get(Hash.HvbEnergyToEmpty.value, None):
                            self._charging_session[Hash.HvbEnergyToEmpty.value] = hvb_ete
                            _LOGGER.debug(f"Saved hvb_ete initial value: {hvb_ete:.03f}")
                    if self._charging_session.get(Hash.HvbSOC.value) is None:
                        if soc := self._vehicle_state.get(Hash.HvbSOC.value, None):
                            self._charging_session[Hash.HvbSOC.value] = soc
                            _LOGGER.debug(f"Saved soc initial value: {soc:.03f}")
                    if self._charging_session.get(Hash.HvbSOCDisplayed.value) is None:
                        if soc_displayed := self._vehicle_state.get(Hash.HvbSOCDisplayed.value, None):
                            self._charging_session[Hash.HvbSOCDisplayed.value] = soc_displayed
                            _LOGGER.debug(f"Saved socd initial value: {soc_displayed:.01f}")
                    if self._charging_session.get(Hash.GpsLatitude.value) is None:
                        if latitude := self._vehicle_state.get(Hash.GpsLatitude.value, None):
                            self._charging_session[Hash.GpsLatitude.value] = latitude
                            _LOGGER.debug(f"Saved latitude initial value: {latitude:.05f}")
                    if self._charging_session.get(Hash.GpsLongitude.value) is None:
                        if longitude := self._vehicle_state.get(Hash.GpsLongitude.value, None):
                            self._charging_session[Hash.GpsLongitude.value] = longitude
                            _LOGGER.debug(f"Saved longitude initial value: {longitude:.05f}")
                    if self._charging_session.get(Hash.HiresOdometer.value) is None:
                        if hires_odometer := self._vehicle_state.get(Hash.HiresOdometer.value, None):
                            self._charging_session[Hash.HiresOdometer.value] = hires_odometer
                            _LOGGER.debug(f"Saved hires_odometer initial value: {hires_odometer:.01f}")

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
                    self.change_state(VehicleState.Charging_Ended)
                else:
                    assert self._vehicle_state.get(Hash.HvbEnergyToEmpty.value, None) is not None
                    assert self._vehicle_state.get(Hash.HvbSOC.value, None) is not None
                    assert self._vehicle_state.get(Hash.HvbSOCDisplayed.value, None) is not None
                    assert self._vehicle_state.get(Hash.GpsLatitude.value, None) is not None
                    assert self._vehicle_state.get(Hash.GpsLongitude.value, None) is not None
                    assert self._vehicle_state.get(Hash.HiresOdometer.value, None) is not None

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
