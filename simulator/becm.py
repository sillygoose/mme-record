import struct

from pid import PID
from can_module import Module


class PID_4800(PID):
    def __init__(self) -> None:
        self._state = 0x40
        super().__init__(0x4800, 'HvbTemp')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_4801(PID):
    def __init__(self) -> None:
        self._state = 0x7A86
        super().__init__(0x4801, 'HvbSoc')

    def response(self) -> bytearray:
        return struct.pack('>BHH', 0x62, self._id, self._state)

class PID_480D(PID):
    def __init__(self) -> None:
        self._state = 0x8ABD
        super().__init__(0x480D, 'HvbV')

    def response(self) -> bytearray:
        return struct.pack('>BHH', 0x62, self._id, self._state)

class PID_4845(PID):
    def __init__(self) -> None:
        self._state = 0x84
        super().__init__(0x4845, 'HvbSocD')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_4848(PID):
    def __init__(self) -> None:
        self._state = 0x63C5
        super().__init__(0x4848, 'EnergyToEmpty')

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHH', 0x62, self._id, self._state)

class PID_484F(PID):
    def __init__(self) -> None:
        self._state = 0x03
        super().__init__(0x484F, 'ChargerStatus')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_4851(PID):
    def __init__(self) -> None:
        self._state = 0x06
        super().__init__(0x4851, 'EvseType')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_48F9(PID):
    def __init__(self) -> None:
        self._state = 0x0052
        super().__init__(0x48F9, 'HvbA')

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_48FB(PID):
    def __init__(self) -> None:
        self._state = -1
        super().__init__(0x48FB, 'ChargePowerLimit')

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_490C(PID):
    def __init__(self) -> None:
        self._state = 0xC8
        super().__init__(0x490C, 'HvbSoh')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)


class BECM(Module):
    pids = {
        0x4800: PID_4800(),
        0x4801: PID_4801(),
        0x480D: PID_480D(),
        0x4845: PID_4845(),
        0x4848: PID_4848(),
        0x484F: PID_484F(),
        0x4851: PID_4851(),
        0x48F9: PID_48F9(),
        0x48FB: PID_48FB(),
        0x490C: PID_490C(),
    }

    def __init__(self) -> None:
        super().__init__(name='BECM', channel='can0', arbitration_id=0x7E4, pids=BECM.pids)

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()
