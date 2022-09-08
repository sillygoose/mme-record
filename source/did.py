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
    InferredKey = 0x417D
    EngineStart = 0x41B9
    HvbTemp = 0x4800
    HvbSoc = 0x4801
    HvbContactorStatus = 0x4802
    HvbContactorPositiveLeakVoltage = 0x4803
    HvbContactorNegativeLeakVoltage = 0x4804
    HvbContactorPositiveVoltage = 0x4805
    HvbContactorNegativeVoltage = 0x4806
    HvbVoltage = 0x480D
    HvbContactorPositiveBusLeakResistance = 0x4811
    HvbContactorNegativeBusLeakResistance = 0x4812
    HvbContactorOverallLeakResistance = 0x4813
    HvbContactorOpenLeakResistance = 0x4814
    LvbDcDcLVCurrent = 0x4836
    LvbDcDcHVCurrent = 0x483A
    LvbDcDcEnable = 0x483D
    HvbChargeCurrentRequested = 0x4842
    ChargePlug = 0x4843
    HvbChargeVoltageRequested = 0x4844
    HvbSocD = 0x4845
    HvbEtE = 0x4848
    ChargerOutputVoltage = 0x484A
    ChargingStatus = 0x484D
    ChargerInputPowerAvailable = 0x484E
    ChargerStatus = 0x484F
    ChargerOutputCurrent = 0x4850
    EvseType = 0x4851
    ChargerInputVoltage = 0x485E
    ChargerInputCurrent = 0x485F
    ChargerInputFrequency = 0x4860
    ChargerPilotDutyCycle = 0x4861
    ChargerPilotVoltage = 0x48B6
    EvseDigitalMode = 0x48B7
    HvbMaximumChargeCurrent = 0x48BC
    ChargerMaxPower = 0x48C4
    HvbCHP = 0x48DE
    HvbCHOp = 0x48DF
    HvbCurrent = 0x48F9
    ChargePowerLimit = 0x48FB
    HvbSoH = 0x490C
    GearDisplayed = 0x6310
    Gps = 0x8012
    Time = 0xDD00
    LoresOdometer = 0xDD01
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
class InferredKey(Enum):
    Unknown = 0
    KeyIn = 1
    KeyOut = 2

@unique
class GearCommanded(Enum):
    Park = 70
    Reverse = 60
    Neutral = 50
    Drive = 40
    Low = 20

@unique
class ChargePlugConnected(Enum):
    No = False
    Yes = True

@unique
class EngineStartRemote(Enum):
    No = False
    Yes = True           # Vehicle cannot be driven

@unique
class EngineStartNormal(Enum):
    No = False
    Yes = True           # Vehicle can be driven

@unique
class EngineStartDisable(Enum):
    No = False
    Yes = True           # Vehicle is not running

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
