import logging
import time
from typing import List

from state_engine import get_InferredKey, get_GearCommanded
from state_engine import get_EngineStartRemote, get_EngineStartNormal

from did import InferredKey, GearCommanded
from did import EngineStartRemote, EngineStartNormal

from vehicle_state import VehicleState, CallType
from hash import *


_LOGGER = logging.getLogger('mme')


class Trip:

    def __init__(self) -> None:
        self._trip_log = None

    def trip_starting(self, state_keys: List, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            pass
        return new_state

    def trip_ending(self, state_keys: List, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            pass
        return new_state

    def trip(self, state_keys: List, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            for key in state_keys:
                if gear_commanded := get_GearCommanded(key, 'trip'):
                    if gear_commanded == GearCommanded.Park:
                        if inferred_key := get_InferredKey(Hash.InferredKey, 'trip'):
                            if inferred_key == InferredKey.KeyOut:
                                if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'trip'):
                                    new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                            elif inferred_key == InferredKey.KeyIn:
                                if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'trip'):
                                    new_state = VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory
        return new_state

