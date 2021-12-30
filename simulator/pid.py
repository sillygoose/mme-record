import struct
from typing import Any


class PID:
    def __init__(self, id: int, name: str, packing: str, initial_state: Any) -> None:
        self._id = id
        self._name = name
        self._packing = packing
        self._state = initial_state

    def response(self) -> bytearray:
        return struct.pack('>BH' + self._packing, 0x62, self._id, self._state)

    def id(self) -> int:
        return self._id

    def name(self) -> str:
        return self._name

    def packing(self) -> str:
        return self._packing

