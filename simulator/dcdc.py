import struct

from pid import PID
from module import Module


class PID_4836(PID):
    def __init__(self) -> None:
        self._state = 0x1B
        super().__init__(0x4836, 'LvbLvCurrent')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_483A(PID):
    def __init__(self) -> None:
        self._state = 0x3A
        super().__init__(0x483A, 'LvbHvCurrent')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_483D(PID):
    def __init__(self) -> None:
        self._state = 0x186
        super().__init__(0x483D, 'LvbDcdcEnable')

    def response(self) -> bytearray:
        return struct.pack('>BHH', 0x62, self._id, self._state)


class DCDC(Module):
    pids = [
        PID_4836(),
        PID_483A(),
        PID_483D(),
    ]

    def __init__(self) -> None:
        super().__init__(name='DCDC', channel='can0', arbitration_id=0x746, pids=DCDC.pids)

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()
