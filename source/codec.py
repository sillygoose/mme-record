from enum import Enum, auto

import udsoncan.configs


class CodecId(Enum):
        Null = auto()
        KeyState = auto()
        GearDisplayed = auto()
        GearCommanded = auto()
        Odometer = auto()
        HiresSpeed = auto()
        ExteriorTemp = auto()
        InteriorTemp = auto()
        Time = auto()
        HvbSoc = auto()
        HvbSocD = auto()
        HvbEte = auto()
        HvbTemp = auto()
        HvbVoltage = auto()
        HvbCurrent = auto()
        LvbSoc = auto()
        LvbVoltage = auto()
        LvbCurrent = auto()
        ChargerStatus = auto()
        EvseDigitalMode = auto()
        EvseType = auto()


class Codec(udsoncan.Did):
    def encode(self, val):
        return val

