import time
import struct
import logging

import isotp
from can.interfaces.socketcan import SocketcanBus

from pid import PID
from can_module import Module


_LOGGER = logging.getLogger('mme')


class PID_411F(PID):
    def __init__(self) -> None:
        self._keystate = 5
        super().__init__(0x411F, 'KeyState')        ### check it?

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._keystate)


class PID_8012(PID):
    def __init__(self) -> None:
        self._elevation = 100
        self._latitude = 2577
        self._longitude = -4610
        self._fix = 4
        self._speed = 12
        self._heading = 256
        self._state = 50
        super().__init__(0x8012, 'GPS')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHHllBHH', 0x62, self._id, self._elevation, self._latitude, self._longitude, self._fix, self._speed, self._heading)


class APIM(Module):
    pids = {
        0x411F: PID_411F(),
        0x8012: PID_8012(),
    }

    def __init__(self) -> None:
        super().__init__(name='APIM', channel='can1', arbitration_id=0x7D0, pids=APIM.pids)

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()
