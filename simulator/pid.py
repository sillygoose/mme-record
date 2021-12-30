import struct
import logging


_LOGGER = logging.getLogger('mme')

_PIDS = [

]

class PID:
    def __init__(self, id: int, name: str, packing: str, states: dict) -> None:
        self._id = id
        self._name = name
        self._packing = packing
        self._states = []
        for state_dict in states:
            state = state_dict.get('state')
            # variable = state.get('name', None)
            value = state.get('value', None)
            self._states.append(value)

    def response(self) -> bytearray:
        response = struct.pack('>BH', 0x62, self._id)
        index = 0
        for state in self._states:
            if self._packing[index] == 'T':
                packing_format = '>L'
            elif self._packing[index] == 't':
                packing_format = '>l'
            else:
                packing_format = '>' + self._packing[index]
            postfix = struct.pack(packing_format, state)
            if self._packing[index] == 'T' or self._packing[index] == 't':
                # Pack as uint then remove high order byte to get A:B:C
                postfix = postfix[1:4]
            response = response + postfix
            index += 1
        return response

    def id(self) -> int:
        return self._id

    def name(self) -> str:
        return self._name

    def packing(self) -> str:
        return self._packing

