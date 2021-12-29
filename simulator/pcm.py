import struct

from pid import PID
from module import Module


class PID_1505(PID):
    def __init__(self) -> None:
        self._state = 10000
        super().__init__(0x1505, 'HiresSpeed')

    def response(self) -> bytearray:
        return struct.pack('>BHH', 0x62, self._id, self._state)


class PCM(Module):
    pids = [
        PID_1505(),
    ]

    def __init__(self) -> None:
        super().__init__(name='PCM', channel='can0', arbitration_id=0x7E0, pids=PCM.pids)

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()
