import struct

from pid import PID
from module import Module


class PID_4028(PID):
    def __init__(self) -> None:
        self._state = 0x5B
        super().__init__(0x4028, 'LvbSoc')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_402A(PID):
    def __init__(self) -> None:
        self._state = 0x92
        super().__init__(0x402A, 'LvbV')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_402B(PID):
    def __init__(self) -> None:
        self._state = 0x82
        super().__init__(0x402B, 'LvbA')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_417D(PID):
    def __init__(self) -> None:
        self._state = 0x02
        super().__init__(0x417D, 'KeyState')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)


class BCM(Module):
    pids = [
        PID_4028(),
        PID_402A(),
        PID_402B(),
        PID_417D(),
    ]

    def __init__(self) -> None:
        super().__init__(name='BCM', channel='can0', arbitration_id=0x726, pids=BCM.pids)

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()
