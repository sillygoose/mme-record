import struct

from pid import PID
from module import Module


class PID_411F(PID):
    def __init__(self) -> None:
        self._state = 5
        super().__init__(0x411F, 'KeyState')        ### check it?

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)


class PID_8012(PID):
    def __init__(self) -> None:
        self._elevation = 100
        self._latitude = 2577
        self._longitude = -4610
        self._fix = 4
        self._speed = 12
        self._heading = 256
        super().__init__(0x8012, 'GPS')

    def response(self) -> bytearray:
        return struct.pack('>BHHllBHH', 0x62, self._id, self._elevation, self._latitude, self._longitude, self._fix, self._speed, self._heading)


class APIM(Module):
    pids = [
        PID_411F(),
        PID_8012(),
    ]

    def __init__(self) -> None:
        super().__init__(name='APIM', channel='can1', arbitration_id=0x7D0, pids=APIM.pids)

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()
