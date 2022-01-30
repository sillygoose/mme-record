import logging
from time import time_ns

from typing import Any, Tuple

from hash import Hash
from did import EngineStartRemote, EngineStartNormal, EngineStartDisable, ChargePlugConnected
from did import KeyState, ChargingStatus, EvseType, GearCommanded, InferredKey


_LOGGER = logging.getLogger('mme')


class StateEngine:

    _state = {}

def get_state_timestamp(hash: Hash) -> int:
    state = StateEngine._state.get(hash, (None, 0))
    return state[1]

def get_state_value(hash: Hash, default_value: Any = None) -> Any:
    state = StateEngine._state.get(hash, (default_value, 0))
    return state[0]

def get_state(hash: Hash, default_value: Any = None) -> Tuple[Any, int]:
    state = StateEngine._state.get(hash, (default_value, 0))
    return state

def set_state(hash: Hash, value: Any) -> int:
    ts = time_ns()
    StateEngine._state[hash] = (value, ts)
    return ts

def hash_fields(hash: Hash) -> Tuple[int, int, str]:
    hash_fields = hash.value.split(':')
    return int(hash_fields[0], base=16), int(hash_fields[1], base=16), hash_fields[2]

def get_KeyState(key: Hash, state: str) -> KeyState:
    key_state = None
    if key == Hash.KeyState:
        try:
            key_state = KeyState(get_state_value(Hash.KeyState))
        except ValueError:
            if key_state := get_state_value(Hash.KeyState):
                _LOGGER.debug(f"While in '{state}', 'KeyState' had an unexpected value: {key_state}")
    return key_state

def get_InferredKey(key: Hash, state: str) -> InferredKey:
    inferred_key = None
    if key == Hash.InferredKey:
        try:
            inferred_key = InferredKey(get_state_value(Hash.InferredKey))
        except ValueError:
            if inferred_key := get_state_value(Hash.InferredKey):
                _LOGGER.debug(f"While in '{state}', 'InferredKey' had an unexpected value: {inferred_key}")
    return inferred_key

def get_ChargingStatus(key: Hash, state: str) -> ChargingStatus:
    charging_status = None
    if key == Hash.ChargingStatus:
        try:
            charging_status = ChargingStatus(get_state_value(Hash.ChargingStatus))
        except ValueError:
            if charging_status := get_state_value(Hash.ChargingStatus):
                _LOGGER.debug(f"While in '{state}', 'ChargingStatus' had an unexpected value: {charging_status}")
    return charging_status

def get_ChargePlugConnected(key: Hash, state: str) -> ChargePlugConnected:
    charge_plug_connected = None
    if key == Hash.ChargePlugConnected:
        try:
            charge_plug_connected = ChargePlugConnected(get_state_value(Hash.ChargePlugConnected))
        except ValueError:
            if charge_plug_connected := get_state_value(Hash.ChargePlugConnected):
                _LOGGER.debug(f"While in '{state}', 'ChargePlugConnected' had an unexpected value: {charge_plug_connected}")
    return charge_plug_connected

def get_GearCommanded(key: Hash, state: str) -> GearCommanded:
    gear_commanded = None
    if key == Hash.GearCommanded:
        try:
            gear_commanded = GearCommanded(get_state_value(Hash.GearCommanded))
        except ValueError:
            if gear_commanded := get_state_value(Hash.GearCommanded):
                _LOGGER.debug(f"While in '{state}', 'GearCommanded' had an unexpected value: {gear_commanded}")
    return gear_commanded

def get_EvseType(key: Hash, state: str) -> EvseType:
    evse_type = None
    if key == Hash.EvseType:
        try:
            evse_type = EvseType(get_state_value(Hash.EvseType))
        except ValueError:
            if evse_type := get_state_value(Hash.EvseType):
                _LOGGER.info(f"While in '{state}', 'EvseType' had an unexpected value: {evse_type}")
    return evse_type

def get_EngineStartNormal(key: Hash, state: str) -> EngineStartNormal:
    engine_start_normal = None
    if key == Hash.EngineStartNormal:
        try:
            engine_start_normal = EngineStartNormal(get_state_value(Hash.EngineStartNormal))
        except ValueError:
            if engine_start_normal := get_state_value(Hash.EngineStartNormal):
                _LOGGER.debug(f"While in '{state}', 'EngineStartNormal' had an unexpected value: {engine_start_normal}")
    return engine_start_normal

def get_EngineStartRemote(key: Hash, state: str) -> EngineStartRemote:
    engine_start_remote = None
    if key == Hash.EngineStartRemote:
        try:
            engine_start_remote = EngineStartRemote(get_state_value(Hash.EngineStartRemote))
        except ValueError:
            if engine_start_remote := get_state_value(Hash.EngineStartRemote):
                _LOGGER.debug(f"While in '{state}', 'EngineStartRemote' had an unexpected value: {engine_start_remote}")
    return engine_start_remote

def get_EngineStartDisable(key: Hash, state: str) -> EngineStartDisable:
    engine_start_disable = None
    if key == Hash.EngineStartDisable:
        try:
            engine_start_disable = EngineStartDisable(get_state_value(Hash.EngineStartDisable))
        except ValueError:
            if engine_start_disable := get_state_value(Hash.EngineStartDisable):
                _LOGGER.debug(f"While in '{state}', 'EngineStartDisable' had an unexpected value: {engine_start_disable}")
    return engine_start_disable
