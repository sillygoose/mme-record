"""
State definitions
"""
from enum import Enum, unique


@unique
class VehicleState(Enum):
        Unknown = 0                 # initial state until another is determined
        Sleeping = 1                # only the GWM responds to ReadDID requests
        Off = 2                     # the vehicle was turned off (but modules are still responding)
        Accessories = 3             # the vehicle start button was pressed with the brake not depressed
        Starting = 4                # this is an intermediate state seen when the start button is held closed (likely insignificant)
        On = 5                      # the vehicle start button was pressed with the brake depressed
        Trip = 6                    # the vehicle is in a gear other than Park
        Preconditioning = 7         # the vehicle is preconditioning
        AC_Charging = 8             # the vehicle is AC charging (Level 1 or Level 2)
        DC_Charging = 9             # the vehicle is DC fast charging


class StateManager:

    _state_file_lookup = {
        VehicleState.Unknown:           'json/unknown.json',
        VehicleState.Sleeping:          'json/sleeping.json',
        VehicleState.Off:               'json/off.json',
        VehicleState.Accessories:       'json/accessories.json',
        VehicleState.Starting:          'json/starting.json',
        VehicleState.On:                'json/on.json',
        VehicleState.Trip:              'json/trip.json',
        VehicleState.Preconditioning:   'json/preconditioning.json',
        VehicleState.AC_Charging:       'json/ac_charging.json',
        VehicleState.DC_Charging:       'json/dc_charging.json',
    }

    def __init__(self, config: dict) -> None:
        self._config = config
        self._state = VehicleState.Unknown
        self._state_function = self.unknown

    def get_current_state_file(self) -> str:
        return StateManager._state_file_lookup.get(self._state, None)

    def get_state_file(self, state:VehicleState) -> str:
        return StateManager._state_file_lookup.get(state, None)

    def unknown(self) -> None:
        pass

    def sleeping(self) -> None:
        pass

    def off(self) -> None:
        pass

    def on(self) -> None:
        pass
