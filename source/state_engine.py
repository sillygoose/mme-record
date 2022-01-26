import logging
from time import time_ns

from typing import Any, Tuple

from hash import Hash


_LOGGER = logging.getLogger('mme')


class StateEngine:

    _state = {}


def get_state_value(hash: Hash, default_value: Any = None) -> Any:
    state = StateEngine._state.get(hash, (default_value, 0))
    return state[0]

def get_state(hash: Hash, default_value: Any = None) -> Tuple[Any, float]:
    state = StateEngine._state.get(hash, default_value)
    return state

def set_state(hash: Hash, value: Any) -> None:
    StateEngine._state[hash] = (value, time_ns())

def hash_fields(hash: Hash) -> Tuple[int, int, str]:
    hash_fields = hash.value.split(':')
    return int(hash_fields[0], base=16), int(hash_fields[1], base=16), hash_fields[2]
