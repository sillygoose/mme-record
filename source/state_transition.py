import logging
from hashlib import sha256

from state_engine import get_InferredKey, get_ChargePlugConnected, get_GearCommanded, get_ChargingStatus, get_KeyState, get_VIN
from state_engine import get_EngineStartRemote, get_EngineStartDisable, get_EngineStartNormal
from state_engine import get_state_value, set_state

from did import InferredKey, ChargePlugConnected, GearCommanded, ChargingStatus, KeyState
from did import EngineStartRemote, EngineStartNormal, EngineStartDisable
from vehicle_state import VehicleState, CallType
from hash import *

from codec_manager import connect_gps_server, CodecManager
from charging import Charging
from trip import Trip


_LOGGER = logging.getLogger('mme')


class StateTransistion(Charging, Trip):

    def __init__(self) -> None:
        Charging.__init__(self)
        Trip.__init__(self)

    def dummy(self, call_type: CallType) -> None:
        _ = call_type

    _requiredUnknownHashes = [
            Hash.VehicleID
        ]

    def unknown(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Incoming:
            pass

        elif call_type == CallType.Outgoing:
            pass

        elif call_type == CallType.Default:
            if inferred_key := get_InferredKey('unknown'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote('unknown'):
                        new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                if inferred_key == InferredKey.KeyIn:
                    if engine_start_disable := get_EngineStartDisable('unknown'):
                        new_state = VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory

            for unknownHash in StateTransistion._requiredUnknownHashes:
                if (hash_value := get_state_value(unknownHash, None)) is None:
                    arbitration_id, did_id, _ = get_hash_fields(unknownHash)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: Waiting for required DID: '{unknownHash.name}'")
                    return VehicleState.Unchanged

            if vin := get_VIN('unknown'):
                set_state(Hash.Vehicle, vin)
                set_state(Hash.VehicleID, vin) ### duplicates?
###                self._unknownHashes[hash] = hash_value

###            if vin := get_VIN('unknown'):
###                vin_hash = hash(vin)
###                set_state(Hash.VehicleHash, vin_hash)
###                print(f"{vin}: {hex(vin_hash)}")
###            else:
###                new_state = VehicleState.Unchanged

        return new_state

    def idle(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if inferred_key := get_InferredKey('idle'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote('idle'):
                        new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_disable := get_EngineStartDisable('idle'):
                        new_state = VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory
            if charge_plug_connected := get_ChargePlugConnected('idle'):
                if charge_plug_connected == ChargePlugConnected.Yes:
                    new_state = VehicleState.PluggedIn
        return new_state

    def accessory(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if inferred_key := get_InferredKey('accessory'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote('accessory'):
                        new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_disable := get_EngineStartDisable('accessory'):
                        new_state = VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory
            if charge_plug_connected := get_ChargePlugConnected('accessory'):
                if charge_plug_connected == ChargePlugConnected.Yes:
                    new_state = VehicleState.PluggedIn
        return new_state

    def on(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Incoming:
            if not CodecManager._gps_server_enabled:
                _LOGGER.info(f"Checking for precise GPS server at '{CodecManager._gps_server}'")
                connect_gps_server()
            return new_state

        if call_type == CallType.Default:
            if inferred_key := get_InferredKey('on'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote('on'):
                        new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_disable := get_EngineStartDisable('on'):
                        new_state = VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory
            if charge_plug_connected := get_ChargePlugConnected('on'):
                if charge_plug_connected == ChargePlugConnected.Yes:
                    new_state = VehicleState.PluggedIn
            if gear_commanded := get_GearCommanded('on'):
                if gear_commanded != GearCommanded.Park:
                    new_state = VehicleState.Trip_Starting
        return new_state

    def preconditioning(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if charging_status := get_ChargingStatus('preconditioning'):
                if charging_status == ChargingStatus.Charging:
                    pass
                elif charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Done:
                    ### fix this
                    if key_state := get_KeyState('preconditioning'):
                        if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                            new_state = VehicleState.Idle
                        elif key_state == KeyState.On or key_state == KeyState.Cranking:
                            new_state = VehicleState.On
                else:
                    _LOGGER.info(f"While in {VehicleState.Preconditioning.name}, 'ChargingStatus' returned an unexpected response: {charging_status}")
            if remote_start := get_EngineStartRemote('preconditioning'):
                if remote_start == EngineStartRemote.No:
                    new_state = VehicleState.Unknown
        return new_state

    def plugged_in(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if charge_plug_connected := get_ChargePlugConnected('plugged_in'):
                if charge_plug_connected == ChargePlugConnected.No:
                    if inferred_key := get_InferredKey('plugged_in'):
                        if inferred_key == InferredKey.KeyOut:
                            if engine_start_remote := get_EngineStartRemote('plugged_in'):
                                new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                        elif inferred_key == InferredKey.KeyIn:
                            if engine_start_normal := get_EngineStartNormal('plugged_in'):
                                new_state = VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory
            if charging_status := get_ChargingStatus('plugged_in'):
                if charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Wait:
                    pass
                elif charging_status == ChargingStatus.Ready or charging_status == ChargingStatus.Charging:
                    new_state = VehicleState.Charge_Starting
                else:
                    _LOGGER.info(f"While in {VehicleState.PluggedIn.name}, 'ChargingStatus' returned an unexpected state: {charging_status}")
        return new_state

