import struct

from pid import PID
from module import Module


class PID_404C(PID):
    def __init__(self) -> None:
        self._state = 10000
        super().__init__(0x404C, 'Odometer')

    def response(self) -> bytearray:
        # Pack as uint then remove high order byte to get A:B:C
        packed = struct.pack('>BHI', 0x62, self._id, self._state)
        return packed[:3] + packed[4:]

class PID_6310(PID):
    def __init__(self) -> None:
        self._state = 1
        super().__init__(0x6310, 'GearSelected')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state) 


class IPC(Module):
    pids = [
        PID_404C(),
        PID_6310(),
    ]

    def __init__(self) -> None:
        super().__init__(name='IPC', channel='can1', arbitration_id=0x720, pids=IPC.pids)

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()
