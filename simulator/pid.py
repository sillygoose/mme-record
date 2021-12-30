import struct


class PID:
    def __init__(self, id: int, name: str, packing: str, states: dict) -> None:
        self._id = id
        self._name = name
        self._packing = packing
        self._states = []
        for state_dict in states:
            state = state_dict.get('state')
            variable = state.get('name', None)
            value = state.get('value', None)
            self._states.append(value)

    def response(self) -> bytearray:
        response = struct.pack('>BH', 0x62, self._id)
        index = 0
        for state in self._states:
            postfix = struct.pack(self._packing[index], state)
            response = response + postfix
            index += 1
        return response

    def id(self) -> int:
        return self._id

    def name(self) -> str:
        return self._name

    def packing(self) -> str:
        return self._packing

