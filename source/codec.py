from enum import Enum, unique

import udsoncan.configs


@unique
class CodecId(Enum):
        Null = -1
        KeyState = 0x411F
        GearDisplayed = 0x6310
        GearCommanded = 0x1E12
        Odometer = 0x404C
        HiresSpeed = 0x1505
        ExteriorTemp = 0xDD05
        InteriorTemp = 0xDD04
        Time = 0xDD00
        Gps = 0x8012
        HvbSoc = 0x4801
        HvbSocD = 0x4845
        HvbEte = 0x4848
        HvbTemp = 0x4800
        HvbVoltage = 0x480D
        HvbCurrent = 0x48F9
        LvbSoc = 0x4028
        LvbVoltage = 0x402A
        LvbCurrent = 0x402B
        ChargerStatus = 0x484F
        EvseDigitalMode = 0x48B7
        EvseType = 0x4851
        HvbSOH = 0x490C
        ChargerInputVoltage = 0x485E
        ChargerInputCurrent = 0x485F
        ChargerInputFrequency = 0x4860
        ChargerPilotVoltage = 0x48B6
        ChargerPilotDutyCycle = 0x4861
        ChargerInputPower = 0x484E
        ChargerMaxPower = 0x48C4
        ChargerOutputVoltage = 0x484A
        ChargerOutputCurrent = 0x4850
        ChargePowerLimit = 0x48FB
        HvbChargeCurrentRequested = 0x4842
        HvbChargeVoltageRequested = 0x4844
        HvbMaximumChargeCurrent = 0x48BC
        LvbDcDcEnable = 0x483D
        LvbDcDcHVCurrent = 0x483A
        LvbDcDcLVCurrent = 0x4836


class Codec(udsoncan.DidCodec):
    def encode(self, val):
        return val
