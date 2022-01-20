"""
State definitions
"""
import logging
from threading import Lock
from queue import PriorityQueue
from time import time
import json

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


@unique
class Hash(Enum):
    KeyState                = '0716:411F:key_state'
    InferredKey             = '0726:417D:inferred_key'
    EvseType                = '07E4:4851:evse_type'
    ChargingStatus          = '07E4:484D:charging_status'
    GearCommanded           = '07E2:1E12:gear_commanded'
    ChargePlugConnected     = '07E2:4843:charge_plug_connected'

    EngineStartNormal       = '0726:41B9:engine_start_normal'
    EngineStartDisable      = '0726:41B9:engine_start_disable'
    EngineStartRemote       = '0726:41B9:engine_start_remote'

    HvbVoltage              = '07E4:480D:hvb_voltage'
    HvbCurrent              = '07E4:48F9:hvb_current'
    HvbPower                = 'FFFF:8000:hvb_power'

    LvbVoltage              = '0726:402A:lvb_voltage'
    LvbCurrent              = '0726:402B:lvb_current'
    LvbPower                = 'FFFF:8001:lvb_power'

    ChgInputVoltage         = '07E2:485E:chg_input_voltage'
    ChgInputCurrent         = '07E2:485F:chg_input_current'
    ChgInputPower           = 'FFFF:8002:chg_input_power'

    ChgOutputVoltage        = '07E2:484A:chg_output_voltage'
    ChgOutputCurrent        = '07E2:4850:chg_output_current'
    ChgOutputPower          = 'FFFF:8003:chg_output_power'


class StateManager:

    _state_file_lookup = {
        VehicleState.Unknown:           {'state_file': 'json/state/unknown.json',           'state_keys': [Hash.InferredKey]},
        VehicleState.Off:               {'state_file': 'json/state/off.json',               'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected]},
        VehicleState.Accessory:         {'state_file': 'json/state/accessory.json',         'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected]},
        VehicleState.On:                {'state_file': 'json/state/on.json',                'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected, Hash.GearCommanded]},
        VehicleState.PluggedIn:         {'state_file': 'json/state/pluggedin.json',         'state_keys': [Hash.ChargePlugConnected, Hash.ChargingStatus]},
        VehicleState.Charging_AC:       {'state_file': 'json/state/charging_ac.json',       'state_keys': [Hash.ChargePlugConnected, Hash.ChargingStatus]},
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
        Hash.ChgInputVoltage:           Hash.ChgInputPower,
        Hash.ChgInputCurrent:           Hash.ChgInputPower,
        Hash.ChgOutputVoltage:          Hash.ChgOutputPower,
        Hash.ChgOutputCurrent:          Hash.ChgOutputPower,
    }

    def __init__(self) -> None:
        self._state = None
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

    def _load_queue(self, module_read_commands: List[dict]) -> None:
        with self._command_queue_lock:
            while not self._command_queue.empty():
                self._command_queue.get_nowait()
            for module in module_read_commands:
                enable = module.get('enable', True)
                if enable:
                    period = module.get('period', 5)
                    payload = (time(), period, [module])
                    self._command_queue.put(payload)

    def _outgoing_state(self, state: VehicleState) -> None:
        if state == VehicleState.Charging_AC:
            delta_hvb_ete = self._vehicle_state.get('07E4:4848:hvb_ete') - self._ac_charging.get('ete')
            #delta_soc = self._vehicle_state.get('07E4:4845:hvb_soc_displayed') - self._ac_charging.get('soc')
            delta_time = int(time()) - self._ac_charging.get('time')
            self._ac_charging = None
            _LOGGER.info(f"Charging session: started: {self._ac_charging.get('time')}, ended: {int(time())}, duration: {delta_time} s, start SOC: {self._ac_charging.get('hvb_socd'):.1f}, end SOC: {self._vehicle_state['07E4:4845:hvb_socd']:.1f}, energy added: {delta_hvb_ete:.1f}")

    def _incoming_state(self, state: VehicleState) -> None:
        if state == VehicleState.Charging_AC:
            self._ac_charging = None

    def change_state(self, new_state: VehicleState) -> None:
        if self._state == new_state:
            return
        if self._state is None:
            _LOGGER.info(f"Vehicle state set to '{new_state.name}'")
        else:
            _LOGGER.info(f"Vehicle state changed from '{self._state.name}' to '{new_state.name}'")

        self._outgoing_state(self._state)
        self._state = new_state
        self._state_time = time()
        self._state_file = StateManager._state_file_lookup.get(new_state).get('state_file')
        self._state_function = StateManager._state_file_lookup.get(new_state).get('state_function')
        queue_commands = self._load_state_definition(self._state_file)
        self._load_queue(queue_commands)
        self._incoming_state(self._state)

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
                    self._vehicle_state[Hash.HvbPower] = hvb_power
                    arbitration_id, did_id, synthetic_name = self._hash_fields(Hash.HvbPower)
                    synthetic = {'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': hvb_power}
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: HVB power is {hvb_power:.0f} W (calculated)")
                elif synthetic_hash == Hash.LvbPower:
                    lvb_power = self._vehicle_state.get(Hash.LvbVoltage.value, 0.0) * self._vehicle_state.get(Hash.LvbCurrent.value, 0.0)
                    self._vehicle_state[Hash.LvbPower] = lvb_power
                    arbitration_id, did_id, synthetic_name = self._hash_fields(Hash.LvbPower)
                    synthetic = {'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': lvb_power}
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: LVB power is {lvb_power:.0f} W (calculated)")
                elif synthetic_hash == Hash.ChgInputPower:
                    chg_input_power = self._vehicle_state.get(Hash.ChgInputVoltage.value, 0.0) * self._vehicle_state.get(Hash.ChgInputCurrent.value, 0.0)
                    self._vehicle_state[Hash.ChgInputPower] = chg_input_power
                    arbitration_id, did_id, synthetic_name = self._hash_fields(Hash.ChgInputPower)
                    synthetic = {'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': chg_input_power}
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger input power is {chg_input_power:.0f} W (calculated)")
                elif synthetic_hash == Hash.ChgOutputPower:
                    chg_output_power = self._vehicle_state.get(Hash.ChgOutputVoltage.value, 0.0) * self._vehicle_state.get(Hash.ChgOutputCurrent.value, 0.0)
                    self._vehicle_state[Hash.ChgOutputPower] = chg_output_power
                    arbitration_id, did_id, synthetic_name = self._hash_fields(Hash.ChgOutputPower)
                    synthetic = {'arbitration_id': arbitration_id, 'did_id': did_id, 'name': synthetic_name, 'value': chg_output_power}
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: AC charger output power is {chg_output_power:.0f} W (calculated)")
        except ValueError:
            pass
        return synthetic

    def update_vehicle_state(self, state_change: dict) -> List[dict]:
        state_data = []
        if state_change.get('type', None) is None:
            did_id = state_change.get('did_id', None)
            if did_id:
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
                if charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Done or charging_status == ChargingStatus.Wait:
                    pass
                elif charging_status == ChargingStatus.Charging:
                    if evse_type := self._get_EvseType(Hash.EvseType):
                        if evse_type == EvseType.BasAC:
                            self.change_state(VehicleState.Charging_AC)
                        elif evse_type != EvseType.NoType:
                            _LOGGER.info(f"While in '{self._state.name}', 'EvseType' returned an unexpected response: {evse_type}")
                elif charging_status == ChargingStatus.Ready:
                    pass
                else:
                    _LOGGER.info(f"While in {self._state}, 'ChargingStatus' returned an unexpected response: {charging_status}")

    def charging_ac(self) -> None:
        # 'state_keys': [Hash.ChargePlugConnected, Hash.ChargingStatus]},
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
                else:
                    hvb_ete = self._vehicle_state.get('07E4:4848:hvb_ete', None)
                    soc = self._vehicle_state.get('07E4:4845:hvb_soc_displayed', None)
                    if self._ac_charging is None:
                        if hvb_ete and soc:
                            self._ac_charging = {'time': int(time()), 'soc': soc, 'ete': hvb_ete}

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
