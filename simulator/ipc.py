import struct

from pid import PID
from can_module import Module


class PID_404C(PID):
    def __init__(self) -> None:
        self._state = 0x00dc66
        super().__init__(0x404C, 'Odometer')

    def response(self) -> bytearray:
        return struct.pack('>BHBBB', 0x62, self._id, ((self._state & 0xff0000) >> 16), ((self._state & 0x00ff00) >> 8), (self._state & 0x0000ff))

class PID_6310(PID):
    def __init__(self) -> None:
        self._state = 1
        super().__init__(0x6310, 'GearSelected')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state) 


class IPC(Module):
    pids = {
        0x404C: PID_404C(),
        0x6310: PID_6310(),
    }

    def __init__(self) -> None:
        super().__init__(name='IPC', channel='can1', arbitration_id=0x720, pids=IPC.pids)

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()
