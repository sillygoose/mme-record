from enum import Enum, unique

@unique
class DidId(Enum):
    Null = -1
    HiresSpeed = 0x1505
    GearCommanded = 0x1E12
    LvbSoc = 0x4028
    LvbVoltage = 0x402A
    LvbCurrent = 0x402B
    HiresOdometer = 0x404C
    KeyState = 0x411F
    EngineStart = 0x41B9
    HvbTemp = 0x4800
    HvbSoc = 0x4801
    HvbVoltage = 0x480D
    LvbDcDcLVCurrent = 0x4836
    LvbDcDcHVCurrent = 0x483A
    LvbDcDcEnable = 0x483D
    HvbChargeCurrentRequested = 0x4842
    HvbChargeVoltageRequested = 0x4844
    HvbSocD = 0x4845
    HvbEte = 0x4848
    ChargerOutputVoltage = 0x484A
    ChargingStatus = 0x484D
    ChargerInputPowerAvailable = 0x484E
    ChargerOutputCurrent = 0x4850
    EvseType = 0x4851
    ChargerInputVoltage = 0x485E
    ChargerInputCurrent = 0x485F
    ChargerInputFrequency = 0x4860
    ChargerPilotDutyCycle = 0x4861
    HvbCurrent = 0x48F9
    ChargerStatus = 0x484F
    ChargerPilotVoltage = 0x48B6
    EvseDigitalMode = 0x48B7
    HvbMaximumChargeCurrent = 0x48BC
    ChargerMaxPower = 0x48C4
    ChargePowerLimit = 0x48FB
    HvbSOH = 0x490C
    GearDisplayed = 0x6310
    Gps = 0x8012
    Time = 0xDD00
    InteriorTemp = 0xDD04
    ExteriorTemp = 0xDD05
    EngineRunTime = 0xF41F


@unique
class KeyState(Enum):
    Sleeping = 0
    On = 3
    Cranking = 4
    Off = 5

@unique
class GearCommanded(Enum):
    Park = 70
    Reverse = 60
    Neutral = 50
    Drive = 40
    Low = 20

@unique
class EngineStartRemote(Enum):
    Off = False
    On = True

@unique
class ChargingStatus(Enum):
    NotReady = 0
    Wait = 1
    Ready = 2
    Charging = 3
    Done = 4
    Fault = 5

@unique
class EvseType(Enum):
    NoType = 0
    Level1 = 1
    Level2 = 2
    DC = 3
    Bas = 4
    HL = 5
    BasAC = 6
    HLAC = 7
    HLDC = 8
    Unknown = 9
    NCom = 10
    Fault = 11
    HEnd = 12
