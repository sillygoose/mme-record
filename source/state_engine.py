import logging
from time import time_ns

from typing import Any, Tuple

from hash import Hash, get_hash_fields
from did import EngineStartRemote, EngineStartNormal, EngineStartDisable, ChargePlugConnected
from did import KeyState, ChargingStatus, EvseType, GearCommanded, InferredKey


_LOGGER = logging.getLogger('mme')


class StateEngine:

    _state = {}
    _did_cache = {}

def initialize_did_cache() -> None:
    StateEngine._did_cache = {}

def get_did_cache(key: str) -> Any:
    return StateEngine._did_cache.get(key, None)

def set_did_cache(key: str, value: Any) -> None:
    StateEngine._did_cache[key] = value

def delete_did_cache(hash: Hash) -> None:
    try:
        arbitration_id, did_id, _ = get_hash_fields(hash)
        key = f"{arbitration_id:04X}:{did_id:04X}"
        StateEngine._did_cache.pop(key)
        _LOGGER.debug(f"Deleted DID cache entry '{hash}'")
    except KeyError:
        _LOGGER.debug(f"Deleting DID cache entry '{hash}' failed")
        pass


def get_state_timestamp(hash: Hash) -> int:
    state = StateEngine._state.get(hash, (None, 0))
    return state[1]

def get_state_value(hash: Hash, default_value: Any = None) -> Any:
    state = StateEngine._state.get(hash, (default_value, 0))
    return state[0]

def get_state(hash: Hash, default_value: Any = None) -> Tuple[Any, int]:
    state = StateEngine._state.get(hash, (default_value, 0))
    return state

def set_state(hash: Hash, value: Any) -> Any:
    StateEngine._state[hash] = (value, time_ns())
    return value

def set_state_interval(hash: Hash, value: Any) -> int:
    ts = time_ns()
    StateEngine._state[hash] = (value, ts)
    return ts

def delete_state(hash: Hash, delete_cache: bool = False) -> None:
    try:
        StateEngine._state.pop(hash)
        if delete_cache:
            delete_did_cache(hash)
    except KeyError:
        pass

def get_KeyState(state: str) -> KeyState:
    try:
        return KeyState(get_state_value(Hash.KeyState))
    except ValueError:
        if key_state := get_state_value(Hash.KeyState):
            _LOGGER.debug(f"While in '{state}', 'KeyState' had an unexpected value: {key_state}")
        return None

def get_InferredKey(state: str) -> InferredKey:
    try:
        return InferredKey(get_state_value(Hash.InferredKey))
    except ValueError:
        if inferred_key := get_state_value(Hash.InferredKey):
            _LOGGER.debug(f"While in '{state}', 'InferredKey' had an unexpected value: {inferred_key}")
        return None

def get_VIN(state: str) -> str:
    try:
        return get_state_value(Hash.VehicleID)
    except ValueError:
        if vin := get_state_value(Hash.VehicleID):
            _LOGGER.debug(f"While in '{state}', 'VehicleID' had an unexpected value: {vin}")
        return None

def get_ChargingStatus(state: str) -> ChargingStatus:
    try:
        return ChargingStatus(get_state_value(Hash.ChargingStatus))
    except ValueError:
        if charging_status := get_state_value(Hash.ChargingStatus):
            _LOGGER.debug(f"While in '{state}', 'ChargingStatus' had an unexpected value: {charging_status}")
        return None

def get_ChargePlugConnected(state: str) -> ChargePlugConnected:
    try:
        return ChargePlugConnected(get_state_value(Hash.ChargePlugConnected))
    except ValueError:
        if charge_plug_connected := get_state_value(Hash.ChargePlugConnected):
            _LOGGER.debug(f"While in '{state}', 'ChargePlugConnected' had an unexpected value: {charge_plug_connected}")
        return None

def get_GearCommanded(state: str) -> GearCommanded:
    try:
        return GearCommanded(get_state_value(Hash.GearCommanded))
    except ValueError:
        if gear_commanded := get_state_value(Hash.GearCommanded):
            _LOGGER.debug(f"While in '{state}', 'GearCommanded' had an unexpected value: {gear_commanded}")
        return None

def get_EvseType(state: str) -> EvseType:
    try:
        return EvseType(get_state_value(Hash.EvseType))
    except ValueError:
        if evse_type := get_state_value(Hash.EvseType):
            _LOGGER.info(f"While in '{state}', 'EvseType' had an unexpected value: {evse_type}")
        return evse_type

def get_EngineStartNormal(state: str) -> EngineStartNormal:
    try:
        return EngineStartNormal(get_state_value(Hash.EngineStartNormal))
    except ValueError:
        if engine_start_normal := get_state_value(Hash.EngineStartNormal):
            _LOGGER.debug(f"While in '{state}', 'EngineStartNormal' had an unexpected value: {engine_start_normal}")
        return None

def get_EngineStartRemote(state: str) -> EngineStartRemote:
    try:
        return EngineStartRemote(get_state_value(Hash.EngineStartRemote))
    except ValueError:
        if engine_start_remote := get_state_value(Hash.EngineStartRemote):
            _LOGGER.debug(f"While in '{state}', 'EngineStartRemote' had an unexpected value: {engine_start_remote}")
        return None

def get_EngineStartDisable(state: str) -> EngineStartDisable:
    try:
        return EngineStartDisable(get_state_value(Hash.EngineStartDisable))
    except ValueError:
        if engine_start_disable := get_state_value(Hash.EngineStartDisable):
            _LOGGER.debug(f"While in '{state}', 'EngineStartDisable' had an unexpected value: {engine_start_disable}")
        return None

def odometer_km(raw_odometer: float) -> float:
    return raw_odometer

def odometer_miles(raw_odometer: float) -> float:
    return odometer_km(raw_odometer) * 0.6213712

def speed_kph(raw_speed: float) -> float:
    return raw_speed

def speed_mph(raw_speed: float) -> float:
    return speed_kph(raw_speed) * 0.6213712
