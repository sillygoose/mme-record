import logging

from typing import List
from config.configuration import Configuration

from state_engine import get_InferredKey, get_ChargePlugConnected, get_GearCommanded, get_ChargingStatus, get_KeyState
from state_engine import get_EngineStartRemote, get_EngineStartDisable, get_EngineStartNormal

from did import InferredKey, ChargePlugConnected, GearCommanded, ChargingStatus, KeyState
from did import EngineStartRemote, EngineStartNormal, EngineStartDisable
from vehicle_state import VehicleState, CallType
from hash import *

from charging import Charging
from trip import Trip


_LOGGER = logging.getLogger('mme')


class StateTransistion(Charging, Trip):

    def __init__(self, config: Configuration) -> None:
        Charging.__init__(self, config)
        Trip.__init__(self, config)

    def unknown(self, state_keys: List, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            for key in state_keys:
                if inferred_key := get_InferredKey(key, 'unknown'):
                    if inferred_key == InferredKey.KeyOut:
                        if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'unknown'):
                            new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                    elif inferred_key == InferredKey.KeyIn:
                        if engine_start_disable := get_EngineStartDisable(Hash.EngineStartDisable, 'unknown'):
                            new_state = VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory
        return new_state

    def idle(self, state_keys: List, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            for key in state_keys:
                if inferred_key := get_InferredKey(key, 'idle'):
                    if inferred_key == InferredKey.KeyOut:
                        if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'idle'):
                            new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                    elif inferred_key == InferredKey.KeyIn:
                        if engine_start_disable := get_EngineStartDisable(Hash.EngineStartDisable, 'idle'):
                            new_state = VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory
                elif charge_plug_connected := get_ChargePlugConnected(key, 'idle'):
                    if charge_plug_connected == ChargePlugConnected.Yes:
                        new_state = VehicleState.PluggedIn
        return new_state

    def accessory(self, state_keys: List, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            for key in state_keys:
                if inferred_key := get_InferredKey(key, 'accessory'):
                    if inferred_key == InferredKey.KeyOut:
                        if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'accessory'):
                            new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                    elif inferred_key == InferredKey.KeyIn:
                        if engine_start_disable := get_EngineStartDisable(Hash.EngineStartDisable, 'accessory'):
                            new_state = VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory
                elif charge_plug_connected := get_ChargePlugConnected(key, 'accessory'):
                    if charge_plug_connected == ChargePlugConnected.Yes:
                        new_state = VehicleState.PluggedIn
        return new_state

    def on(self, state_keys: List, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            for key in state_keys:
                if inferred_key := get_InferredKey(key, 'on'):
                    if inferred_key == InferredKey.KeyOut:
                        if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'on'):
                            new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                    elif inferred_key == InferredKey.KeyIn:
                        if engine_start_disable := get_EngineStartDisable(Hash.EngineStartDisable, 'on'):
                            new_state = VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory
                elif charge_plug_connected := get_ChargePlugConnected(key, 'on'):
                    if charge_plug_connected == ChargePlugConnected.Yes:
                        new_state = VehicleState.PluggedIn
                elif gear_commanded := get_GearCommanded(key, 'on'):
                    if gear_commanded != GearCommanded.Park:
                        new_state = VehicleState.Trip_Starting
        return new_state

    def preconditioning(self, state_keys: List, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            for key in state_keys:
                if charging_status := get_ChargingStatus(key, 'preconditioning'):
                    if charging_status == ChargingStatus.Charging:
                        pass
                    elif charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Done:
                        ### fix this
                        if key_state := get_KeyState(Hash.KeyState, 'preconditioning'):
                            if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                                new_state = VehicleState.Idle
                            elif key_state == KeyState.On or key_state == KeyState.Cranking:
                                new_state = VehicleState.On
                    else:
                        _LOGGER.info(f"While in {VehicleState.Preconditioning.name}, 'ChargingStatus' returned an unexpected response: {charging_status}")
                elif remote_start := get_EngineStartRemote(key, 'preconditioning'):
                    if remote_start == EngineStartRemote.No:
                        new_state = VehicleState.Unknown
        return new_state

    def plugged_in(self, state_keys: List, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            for key in state_keys:
                if charge_plug_connected := get_ChargePlugConnected(key, 'plugged_in'):
                    if charge_plug_connected == ChargePlugConnected.No:
                        if inferred_key := get_InferredKey(Hash.InferredKey, 'plugged_in'):
                            if inferred_key == InferredKey.KeyOut:
                                if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'plugged_in'):
                                    new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                            elif inferred_key == InferredKey.KeyIn:
                                if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'plugged_in'):
                                    new_state = VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory
                elif charging_status := get_ChargingStatus(key, 'plugged_in'):
                    if charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Wait:
                        pass
                    elif charging_status == ChargingStatus.Ready or charging_status == ChargingStatus.Charging:
                        new_state = VehicleState.Charging_Starting
                    else:
                        _LOGGER.info(f"While in {VehicleState.PluggedIn.name}, 'ChargingStatus' returned an unexpected state: {charging_status}")
        return new_state

