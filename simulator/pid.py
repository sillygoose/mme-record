import struct
import logging
from typing import List

from exceptions import FailedInitialization


_LOGGER = logging.getLogger('mme')

_PIDS = {
    0x1505: { 'name': 'HiresSpeed',     'packing': 'H',     'modules': ['PCM'],     'states': [{ 'name': 'speed', 'value': 10000}] },
    0x1E12: { 'name': 'GearCommanded',  'packing': 'B',     'modules': ['SOBDM'],   'states': [{ 'name': 'gear_commanded', 'value': 70}] },
}
"""
"""

class PID:
    def __init__(self, id: int) -> None:
        self._id = id
        pid_lookup = _PIDS.get(id, None)
        if pid_lookup is None:
            raise FailedInitialization(f"The PID {id:04X} is not supported by the simulator")

        self._name = pid_lookup.get('name')
        self._packing = pid_lookup.get('packing')
        self._modules = pid_lookup.get('modules')
        self._states = []
        for state in pid_lookup.get('states'):
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

    def used_in(self) -> List[str]:
        return self._modules

