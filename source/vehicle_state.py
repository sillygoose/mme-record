from enum import Enum, unique, auto

@unique
class CallType(Enum):
    Incoming = auto()
    Default = auto()
    Outgoing = auto()


@unique
class VehicleState(Enum):
    Unknown = auto()                # initial state until another is determined
    Unchanged = auto()              # the vehicle state is not changing
    Idle = auto()                   # the vehicle is idle
    Accessory = auto()              # the vehicle is on and in Accessory mode
    On = auto()                     # the vehicle is on and in Drivable mode

    Trip_Starting = auto()          # the vehicle is in a gear other than Park
    Trip = auto()                   # the vehicle is in a gear other than Park
    Trip_Ending = auto()            # the vehicle is in Park again

    PluggedIn = auto()              # the vehicle has plugged in
    Preconditioning = auto()        # the vehicle is preconditioning (remote start)

    Charge_Starting = auto()        # the vehicle is beginning a charging session
    Charge_AC = auto()              # the vehicle is AC charging
    Charge_DCFC = auto()            # the vehicle is DC fast charging
    Charge_Ending = auto()          # the vehicle is no longer charging

