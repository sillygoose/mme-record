import logging
import time

from typing import List

from state_engine import get_InferredKey, get_ChargePlugConnected, get_GearCommanded, get_ChargingStatus, get_KeyState, get_EvseType
from state_engine import get_EngineStartRemote, get_EngineStartDisable, get_EngineStartNormal
from state_engine import get_state_value, set_state

from did import InferredKey, ChargePlugConnected, GearCommanded, ChargingStatus, KeyState, EvseType
from did import EngineStartRemote, EngineStartNormal, EngineStartDisable
from vehicle_state import VehicleState
from hash import *


_LOGGER = logging.getLogger('mme')


class StateTransistion:

    def __init__(self, state_keys: dict) -> None:
        self._state_keys = state_keys
        self._charging_session = None

    def state_keys(self, state: VehicleState) -> List[Hash]:
        return self._state_keys.get(state).get('state_keys')

    def unknown(self) -> VehicleState:
        new_state = VehicleState.Unchanged
        for key in self.state_keys(VehicleState.Unknown):
            if inferred_key := get_InferredKey(key, 'unknown'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'unknown'):
                        new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_disable := get_EngineStartDisable(Hash.EngineStartDisable, 'unknown'):
                        new_state = VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory
        return new_state

    def off(self) -> VehicleState:
        new_state = VehicleState.Unchanged
        for key in self.state_keys(VehicleState.Off):
            if inferred_key := get_InferredKey(key, 'off'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'off'):
                        if engine_start_remote == EngineStartRemote.Yes:
                            new_state = VehicleState.Preconditioning
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'off'):
                        new_state = VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory
            elif charge_plug_connected := get_ChargePlugConnected(key, 'off'):
                if charge_plug_connected == ChargePlugConnected.Yes:
                    new_state = VehicleState.PluggedIn
        return new_state

    def accessory(self) -> VehicleState:
        new_state = VehicleState.Unchanged
        for key in self.state_keys(VehicleState.Accessory):
            if inferred_key := get_InferredKey(key, 'accessory'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'accessory'):
                        new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'accessory'):
                        new_state = VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory
            elif charge_plug_connected := get_ChargePlugConnected(key, 'accessory'):
                if charge_plug_connected == ChargePlugConnected.Yes:
                    new_state = VehicleState.PluggedIn
        return new_state

    def on(self) -> VehicleState:
        new_state = VehicleState.Unchanged
        for key in self.state_keys(VehicleState.On):
            if inferred_key := get_InferredKey(key, 'on'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'on'):
                        new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'on'):
                        new_state = VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory
            elif charge_plug_connected := get_ChargePlugConnected(key, 'on'):
                if charge_plug_connected == ChargePlugConnected.Yes:
                   new_state = VehicleState.PluggedIn
            elif gear_commanded := get_GearCommanded(key, 'on'):
                if gear_commanded != GearCommanded.Park:
                    new_state = VehicleState.Trip
        return new_state

    def trip(self) -> VehicleState:
        new_state = VehicleState.Unchanged
        for key in self.state_keys(VehicleState.Trip):
            if gear_commanded := get_GearCommanded(key, 'trip'):
                if gear_commanded == GearCommanded.Park:
                    if inferred_key := get_InferredKey(Hash.InferredKey, 'trip'):
                        if inferred_key == InferredKey.KeyOut:
                            if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'trip'):
                                new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off
                        elif inferred_key == InferredKey.KeyIn:
                            if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'trip'):
                                new_state = VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory
        return new_state

    def preconditioning(self) -> VehicleState:
        new_state = VehicleState.Unchanged
        for key in self.state_keys(VehicleState.Preconditioning):
            if charging_status := get_ChargingStatus(key, 'preconditioning'):
                if charging_status == ChargingStatus.Charging:
                    pass
                elif charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Done:
                    ### fix this
                    if key_state := get_KeyState(Hash.KeyState, 'preconditioning'):
                        if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                            new_state = VehicleState.Off
                        elif key_state == KeyState.On or key_state == KeyState.Cranking:
                            new_state = VehicleState.On
                else:
                    _LOGGER.info(f"While in {VehicleState.Preconditioning.name}, 'ChargingStatus' returned an unexpected response: {charging_status}")
            elif remote_start := get_EngineStartRemote(key, 'preconditioning'):
                if remote_start == EngineStartRemote.No:
                    new_state = VehicleState.Unknown
        return new_state

    def plugged_in(self) -> VehicleState:
        new_state = VehicleState.Unchanged
        for key in self.state_keys(VehicleState.PluggedIn):
            if charge_plug_connected := get_ChargePlugConnected(key, 'plugged_in'):
                if charge_plug_connected == ChargePlugConnected.No:
                    if inferred_key := get_InferredKey(Hash.InferredKey, 'plugged_in'):
                        if inferred_key == InferredKey.KeyOut:
                            if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'plugged_in'):
                                new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off
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

    def charging_starting(self) -> VehicleState:
        if self._charging_session is None:
            self._charging_session = {
                'time': int(time.time()),
            }

        new_state = VehicleState.Unchanged
        for key in self.state_keys(VehicleState.Charging_Starting):
            if charging_status := get_ChargingStatus(key, 'charging_starting'):
                if charging_status == ChargingStatus.Ready or charging_status == ChargingStatus.Wait or charging_status == ChargingStatus.Charging:
                    if self._charging_session.get(Hash.HvbEtE) is None:
                        if hvb_ete := get_state_value(Hash.HvbEtE, None):
                            self._charging_session[Hash.HvbEtE] = hvb_ete
                            _LOGGER.debug(f"Saved hvb_ete initial value: {hvb_ete:.03f}")
                    if self._charging_session.get(Hash.HvbSoC) is None:
                        if soc := get_state_value(Hash.HvbSoC, None):
                            self._charging_session[Hash.HvbSoC] = soc
                            _LOGGER.debug(f"Saved soc initial value: {soc:.03f}")
                    if self._charging_session.get(Hash.HvbSoCD) is None:
                        if soc_displayed := get_state_value(Hash.HvbSoCD, None):
                            self._charging_session[Hash.HvbSoCD] = soc_displayed
                            _LOGGER.debug(f"Saved socd initial value: {soc_displayed:.01f}")
                    if self._charging_session.get(Hash.GpsLatitude) is None:
                        if latitude := get_state_value(Hash.GpsLatitude, None):
                            self._charging_session[Hash.GpsLatitude] = latitude
                            _LOGGER.debug(f"Saved latitude initial value: {latitude:.05f}")
                    if self._charging_session.get(Hash.GpsLongitude) is None:
                        if longitude := get_state_value(Hash.GpsLongitude, None):
                            self._charging_session[Hash.GpsLongitude] = longitude
                            _LOGGER.debug(f"Saved longitude initial value: {longitude:.05f}")
                    if self._charging_session.get(Hash.LoresOdometer) is None:
                        if lores_odometer := get_state_value(Hash.LoresOdometer, None):
                            self._charging_session[Hash.LoresOdometer] = lores_odometer
                            _LOGGER.debug(f"Saved lores_odometer initial value: {lores_odometer}")
                    if self._charging_session.get(Hash.ChargerInputEnergy) is None:
                        charger_input_energy = get_state_value(Hash.ChargerInputEnergy, 0.0)
                        set_state(Hash.ChargerInputEnergy, charger_input_energy)
                        self._charging_session[Hash.ChargerInputEnergy] = charger_input_energy
                        _LOGGER.debug(f"Saved charger input energy initial value: {charger_input_energy}")
                    if self._charging_session.get(Hash.ChargerOutputEnergy) is None:
                        charger_output_energy = get_state_value(Hash.ChargerOutputEnergy, 0.0)
                        set_state(Hash.ChargerOutputEnergy, charger_output_energy)
                        self._charging_session[Hash.ChargerOutputEnergy] = charger_output_energy
                        _LOGGER.debug(f"Saved charger output energy initial value: {charger_output_energy}")

                    if charging_status == ChargingStatus.Charging:
                        if evse_type := get_EvseType(Hash.EvseType, 'charging_starting'):
                            if evse_type == EvseType.BasAC:
                                new_state = VehicleState.Charging_AC
                            elif evse_type != EvseType.NoType:
                                _LOGGER.error(f"While in '{VehicleState.Charging_Starting.name}', 'EvseType' returned an unexpected state: {evse_type}")
                else:
                    _LOGGER.info(f"While in {VehicleState.Charging_Starting.name}, 'ChargingStatus' returned an unexpected response: {charging_status}")
        return new_state

    def charging_ac(self) -> VehicleState:
        new_state = VehicleState.Unchanged
        for key in self.state_keys(VehicleState.Charging_AC):
            if charging_status := get_ChargingStatus(key, 'charging_ac'):
                if charging_status != ChargingStatus.Charging:
                    _LOGGER.debug(f"Charging status changed to: {charging_status}")
                    new_state = VehicleState.Charging_Ended
                else:
                    assert get_state_value(Hash.HvbEtE, None) is not None
                    assert get_state_value(Hash.HvbSoC, None) is not None
                    assert get_state_value(Hash.HvbSoCD, None) is not None
                    assert get_state_value(Hash.GpsLatitude, None) is not None
                    assert get_state_value(Hash.GpsLongitude, None) is not None
                    assert get_state_value(Hash.LoresOdometer, None) is not None
                    assert get_state_value(Hash.ChargerInputEnergy, None) is not None
                    assert get_state_value(Hash.ChargerOutputEnergy, None) is not None
        return new_state

    def charging_ended(self) -> VehicleState:
        new_state = VehicleState.Unchanged
        for key in self.state_keys(VehicleState.Charging_Ended):
            if charging_status := get_ChargingStatus(key, 'charging_ended'):
                if charging_status != ChargingStatus.Charging:
                    if charge_plug_connected := get_ChargePlugConnected(Hash.ChargePlugConnected, 'charging_ended'):
                        if charge_plug_connected == ChargePlugConnected.Yes:
                            new_state = VehicleState.PluggedIn
                        elif inferred_key := get_InferredKey(Hash.InferredKey, 'charging_ended'):
                            if inferred_key == InferredKey.KeyOut:
                                if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'charging_ended'):
                                    new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off
                            elif inferred_key == InferredKey.KeyIn:
                                if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'charging_ended'):
                                    new_state = VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory
        return new_state

    def charging_dcfc(self) -> VehicleState:
        new_state = VehicleState.Unchanged
        for key in self.state_keys(VehicleState.Charging_DCFC):
            if charging_status := get_ChargingStatus(key, 'charging_dcfc'):
                if charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Done:
                    if key_state := get_KeyState(Hash.KeyState):
                        if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                            new_state = VehicleState.Off
                        elif key_state == KeyState.On or key_state == KeyState.Cranking:
                            VehicleState.On
                else:
                    _LOGGER.info(f"While in '{VehicleState.Charging_DCFC.name}', 'ChargingStatus' returned an unexpected response: {charging_status}")
        return new_state
