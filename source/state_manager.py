"""
State definitions
"""
import logging
from enum import Enum, unique

from codec_manager import *


_LOGGER = logging.getLogger('mme')



class StateManager:

    @unique
    class StateDID(Enum):
        KeyState = 0x411F
        EvseType = 0x4851

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
        self._state = StateManager.VehicleState.Unknown
        self._state_function = self.unknown
        self._codec_manager = CodecManager(config=self._config)
        self._vehicle_state = {}

    def get_current_state_file(self) -> str:
        return StateManager._state_file_lookup.get(self._state, None)

    def get_state_file(self, state:VehicleState) -> str:
        return StateManager._state_file_lookup.get(state, None)

    def unknown(self, state_change: dict) -> None:
        _LOGGER.info(state_change)
        if state_change.get('type', None) is None:
            did_id = state_change.get('did_id', None)
            if did_id:
                state_did = StateManager.StateDID(did_id)
                codec = self._codec_manager.codec(did_id)
                decoded = codec.decode(None, bytearray(state_change.get('payload')))
                states = decoded.get('states')
                if state_did == StateManager.StateDID.KeyState:
                    value = states[0].get('key_state', None)
                    self._vehicle_state[did_id] = value
                elif state_did == StateManager.StateDID.EvseType:
                    value = states[0].get('key_state', None)
                    self._vehicle_state[did_id] = value
        else:
            arbitration_id = state_change.get('arbitration_id')
            did_list = state_change.get('did_list')
            pass

    def sleeping(self) -> None:
        pass

    def off(self) -> None:
        pass

    def on(self) -> None:
        pass
