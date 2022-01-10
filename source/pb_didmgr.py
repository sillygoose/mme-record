import struct
import logging

from typing import List


_LOGGER = logging.getLogger('mme')


class PlaybackDID:

    def __init__(self, did_id: int, did_name: str, packing: str, modules: List[str], states: List[dict]) -> None:
        self._did_id = did_id
        self._did_name = did_name
        self._packing = packing
        self._modules = modules
        self._states = []
        for state in states:
            # variable = state.get('name', None)
            value = state.get('value', None)
            self._states.append(value)
        _LOGGER.debug(f"Created DID {self._did_name}:{self._did_id:04X}")

    def response(self) -> bytearray:
        response = bytearray()
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

    def new_event(self, event) -> None:
        payload = bytearray(event.get('payload'))
        unpacking_format = '>' + self._packing
        if self._packing.find('T') >= 0:
            unpacking_format = unpacking_format.replace('T', 'HB')
        unpacked_values = list(struct.unpack(unpacking_format, payload))
        if self._packing.find('T') >= 0:
            unpacked_values[0] = unpacked_values[0] * 256 + unpacked_values[1]
        index = 0
        for _ in self._states:
            self._states[index] = unpacked_values[index]
            index += 1

    def did(self) -> int:
        return self._did_id

    def name(self) -> str:
        return self._did_name

    def packing(self) -> str:
        return self._packing

    def used_in(self) -> List[str]:
        return self._modules
