import struct

from pid import PID
from module import Module


class PID_411F(PID):
    def __init__(self) -> None:
        self._state = 3
        super().__init__(0x411F, 'KeyState')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)


class GWM(Module):
    pids = [
        PID_411F(),     ### right?
    ]

    def __init__(self) -> None:
        super().__init__(name='GWM', channel='can0', arbitration_id=0x716, pids=GWM.pids)

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()
