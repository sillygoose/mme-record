import struct
import time

from pid import PID
from can_module import Module


class PID_1E12(PID):
    def __init__(self) -> None:
        self._state = 50
        super().__init__(0x1E12, 'GearCommanded')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_4842(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x4842, 'HvbChargeCurrentRequested')

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_4844(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x4844, 'HvbChargeVoltageRequested')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_484A(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x484A, 'ChargerOutputVoltage')

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_484E(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x484E, 'ChargerInputPower')

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_4850(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x4850, 'ChargerOutputCurrent')

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_485E(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x485E, 'ChargerInputVoltage')

    def response(self) -> bytearray:
        return struct.pack('>BHH', 0x62, self._id, self._state)

class PID_485F(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x485F, 'ChargerInputCurrent')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_4860(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x4860, 'ChargerInputFrequency')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_4861(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x4861, 'ChargerPilotDutyCycle')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_48B6(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x48B6, 'ChargerPilotVoltage')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_48BC(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x48BC, 'HvbMaximumChargeCurrent')

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_48C4(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x48C4, 'ChargerMaxPower')

    def response(self) -> bytearray:
        return struct.pack('>BHH', 0x62, self._id, self._state)

class PID_DD00(PID):
    def __init__(self) -> None:
        self._state = int(time.time())
        super().__init__(0xDD00, 'GlobalTime')

    def response(self) -> bytearray:
        return struct.pack('>BHI', 0x62, self._id, self._state)

class PID_DD04(PID):
    def __init__(self) -> None:
        self._state = 50
        super().__init__(0xDD04, 'InteriorTemp')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_DD05(PID):
    def __init__(self) -> None:
        self._state = 50
        super().__init__(0xDD05, 'ExteriorTemp')

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)


class SOBDM(Module):
    pids = {
        0x1E12: PID_1E12(),
        0x4842: PID_4842(),
        0x4844: PID_4844(),
        0x484A: PID_484A(),
        0x484E: PID_484E(),
        0x4850: PID_4850(),
        0x485E: PID_485E(),
        0x485F: PID_485F(),
        0x4860: PID_4860(),
        0x4861: PID_4861(),
        0x48B6: PID_48B6(),
        0x48BC: PID_48BC(),
        0x48C4: PID_48C4(),
        0xDD00: PID_DD00(),
        0xDD04: PID_DD04(),
        0xDD05: PID_DD05(),
    }

    def __init__(self) -> None:
        super().__init__(name='SOBDM', channel='can0', arbitration_id=0x7E2, pids=SOBDM.pids)

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()
