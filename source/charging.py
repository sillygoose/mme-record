import logging
import time
import datetime

from typing import List

from state_engine import get_state_value, set_state
from state_engine import get_ChargePlugConnected, get_ChargingStatus, get_EvseType
from state_engine import get_InferredKey, get_EngineStartRemote, get_EngineStartNormal

from did import ChargePlugConnected, ChargingStatus, EvseType
from did import InferredKey, EngineStartRemote, EngineStartNormal

from vehicle_state import VehicleState, CallType
from hash import *

from influxdb import influxdb_charging_session
from geocoding import reverse_geocode


_LOGGER = logging.getLogger('mme')


class Charging:

    def __init__(self) -> None:
        self._charging_session = None

    def charging_starting(self,call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Incoming:
            assert self._charging_session is None
            self._charging_session = {
                'time': int(time.time()),
            }
            set_state(Hash.ChargerInputPowerMax, 0)
            set_state(Hash.ChargerOutputPowerMax, 0)
        elif call_type == CallType.Outgoing:
            assert get_state_value(Hash.HvbEtE, None) is not None
            assert get_state_value(Hash.HvbSoC, None) is not None
            assert get_state_value(Hash.HvbSoCD, None) is not None
            assert get_state_value(Hash.GpsLatitude, None) is not None
            assert get_state_value(Hash.GpsLongitude, None) is not None
            assert get_state_value(Hash.LoresOdometer, None) is not None
            assert get_state_value(Hash.ChargerInputEnergy, None) is not None
            assert get_state_value(Hash.ChargerOutputEnergy, None) is not None
        elif call_type == CallType.Default:
            if charging_status := get_ChargingStatus(Hash.ChargingStatus, 'charging_starting'):
                if charging_status == ChargingStatus.Ready or charging_status == ChargingStatus.Wait or charging_status == ChargingStatus.Charging:
                    if self._charging_session.get(Hash.LvbEnergy) is None:
                        if (lvb_energy := get_state_value(Hash.LvbEnergy, None)) is not None:
                            self._charging_session[Hash.LvbEnergy] = lvb_energy
                            _LOGGER.debug(f"Saved lvb_energy initial value: {lvb_energy:.0f}")
                    if self._charging_session.get(Hash.HvbEtE) is None:
                        if (hvb_ete := get_state_value(Hash.HvbEtE, None)) is not None:
                            self._charging_session[Hash.HvbEtE] = hvb_ete
                            _LOGGER.debug(f"Saved hvb_ete initial value: {hvb_ete:.0f}")
                    if self._charging_session.get(Hash.HvbSoC) is None:
                        if (soc := get_state_value(Hash.HvbSoC, None)) is not None:
                            self._charging_session[Hash.HvbSoC] = soc
                            _LOGGER.debug(f"Saved soc initial value: {soc:.03f}")
                    if self._charging_session.get(Hash.HvbSoCD) is None:
                        if (soc_displayed := get_state_value(Hash.HvbSoCD, None)) is not None:
                            self._charging_session[Hash.HvbSoCD] = soc_displayed
                            _LOGGER.debug(f"Saved socd initial value: {soc_displayed:.01f}")
                    if self._charging_session.get(Hash.GpsLatitude) is None:
                        if (latitude := get_state_value(Hash.GpsLatitude, None)) is not None:
                            self._charging_session[Hash.GpsLatitude] = latitude
                            _LOGGER.debug(f"Saved latitude initial value: {latitude:.05f}")
                    if self._charging_session.get(Hash.GpsLongitude) is None:
                        if (longitude := get_state_value(Hash.GpsLongitude, None)) is not None:
                            self._charging_session[Hash.GpsLongitude] = longitude
                            _LOGGER.debug(f"Saved longitude initial value: {longitude:.05f}")
                    if self._charging_session.get(Hash.LoresOdometer) is None:
                        if (lores_odometer := get_state_value(Hash.LoresOdometer, None)) is not None:
                            self._charging_session[Hash.LoresOdometer] = lores_odometer
                            _LOGGER.debug(f"Saved lores_odometer initial value: {lores_odometer}")
                    if self._charging_session.get(Hash.ChargerInputEnergy) is None:
                        charger_input_energy = get_state_value(Hash.ChargerInputEnergy, 0.0)
                        set_state(Hash.ChargerInputEnergy, charger_input_energy)
                        self._charging_session[Hash.ChargerInputEnergy] = charger_input_energy
                        _LOGGER.debug(f"Saved charger input energy initial value: {charger_input_energy:.0f}")
                    if self._charging_session.get(Hash.ChargerOutputEnergy) is None:
                        charger_output_energy = get_state_value(Hash.ChargerOutputEnergy, 0.0)
                        set_state(Hash.ChargerOutputEnergy, charger_output_energy)
                        self._charging_session[Hash.ChargerOutputEnergy] = charger_output_energy
                        _LOGGER.debug(f"Saved charger output energy initial value: {charger_output_energy:.0f}")

                    if charging_status == ChargingStatus.Charging:
                        if evse_type := get_EvseType(Hash.EvseType, 'charging_starting'):
                            if evse_type == EvseType.BasAC:
                                new_state = VehicleState.Charging_AC
                                self._charging_session['type'] = 'AC'
                            elif evse_type != EvseType.NoType:
                                _LOGGER.error(f"While in '{VehicleState.Charging_Starting.name}', 'EvseType' returned an unexpected state: {evse_type}")
                else:
                    _LOGGER.info(f"While in {VehicleState.Charging_Starting.name}, 'ChargingStatus' returned an unexpected response: {charging_status}")
        return new_state

    def charging_ac(selff, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if charging_status := get_ChargingStatus(Hash.ChargingStatus, 'charging_ac'):
                if charging_status != ChargingStatus.Charging:
                    _LOGGER.debug(f"Charging status changed to: {charging_status}")
                    new_state = VehicleState.Charging_Ended
        return new_state

    def charging_dcfc(self, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if charging_status := get_ChargingStatus(Hash.ChargingStatus, 'charging_dcfc'):
                if charging_status != ChargingStatus.Charging:
                    _LOGGER.debug(f"Charging status changed to: {charging_status}")
                    new_state = VehicleState.Charging_Ended
        return new_state

    def charging_ended(self, call_type: CallType = CallType.Default) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if charging_status := get_ChargingStatus(Hash.ChargingStatus, 'charging_ended'):
                if charging_status != ChargingStatus.Charging:
                    if charge_plug_connected := get_ChargePlugConnected(Hash.ChargePlugConnected, 'charging_ended'):
                        if charge_plug_connected == ChargePlugConnected.Yes:
                            new_state = VehicleState.PluggedIn
                        elif inferred_key := get_InferredKey(Hash.InferredKey, 'charging_ended'):
                            if inferred_key == InferredKey.KeyOut:
                                if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'charging_ended'):
                                    new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                            elif inferred_key == InferredKey.KeyIn:
                                if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'charging_ended'):
                                    new_state = VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory
        elif call_type == CallType.Outgoing:
            charger_type = self._charging_session.get('type')
            starting_time = self._charging_session.get('time')
            ending_time = int(time.time())
            duration_seconds = ending_time - starting_time
            starting_soc = self._charging_session.get(Hash.HvbSoC)
            starting_socd = self._charging_session.get(Hash.HvbSoCD)
            starting_ete = self._charging_session.get(Hash.HvbEtE)
            starting_charging_input_energy = self._charging_session.get(Hash.ChargerInputEnergy, 0.0)
            starting_lvb_energy = self._charging_session.get(Hash.LvbEnergy)
            latitude = self._charging_session.get(Hash.GpsLatitude, 0.0)
            longitude = self._charging_session.get(Hash.GpsLongitude, 0.0)
            odometer = self._charging_session.get(Hash.LoresOdometer, 0)

            ending_soc = get_state_value(Hash.HvbSoC)
            ending_socd = get_state_value(Hash.HvbSoCD)
            ending_ete = get_state_value(Hash.HvbEtE)
            ending_charging_input_energy = get_state_value(Hash.ChargerInputEnergy)
            ending_lvb_energy = get_state_value(Hash.LvbEnergy)
            delta_lvb_energy = ending_lvb_energy - starting_lvb_energy
            delta_hvb_energy = ending_ete - starting_ete
            wh_added = delta_hvb_energy + delta_lvb_energy
            wh_used = ending_charging_input_energy - starting_charging_input_energy
            charging_efficiency = wh_added / wh_used if wh_used > 0 else 0.0
            max_input_power = get_state_value(Hash.ChargerInputPowerMax)
            session_datetime = datetime.datetime.fromtimestamp(starting_time).strftime('%Y-%m-%d %H:%M')
            hours, rem = divmod(duration_seconds, 3600)
            minutes, _ = divmod(rem, 60)
            charging_session = {
                'type':             charger_type,
                'time':             starting_time,
                'duration':         duration_seconds,
                'location':         {'latitude': latitude, 'longitude': longitude},
                'odometer':         odometer,
                'soc':              {'starting': starting_soc, 'ending': ending_soc},
                'socd':             {'starting': starting_socd, 'ending': ending_socd},
                'ete':              {'starting': starting_ete, 'ending': ending_ete},
                'kwh_added':        wh_added * 0.001,
                'kwh_used':         wh_used * 0.001,
                'efficiency':       charging_efficiency,
                'max_power':        max_input_power,
            }
            _LOGGER.info(f"Charging session statistics:")
            _LOGGER.info(f"    {charger_type} charging session started at {session_datetime} for {hours} hours, {minutes} minutes")
            _LOGGER.info(f"    location ({reverse_geocode((latitude, longitude))})")
            _LOGGER.info(f"    starting SoC was {starting_socd:.01f}%, ending SoC was {ending_socd:.01f}%")
            _LOGGER.info(f"    starting EtE was {starting_ete:.0f} Wh, ending EtE was {ending_ete:.0f} Wh, LVB delta energy was {delta_lvb_energy:.0f} Wh")
            _LOGGER.info(f"    {wh_added:.0f} Wh were added, requiring {wh_used:.0f} Wh from the AC charger")
            _LOGGER.info(f"    overall efficiency is {(charging_efficiency*100):.01f}%")
            _LOGGER.info(f"    maximum input power {max_input_power:.0f} W")
            influxdb_charging_session(session=charging_session, vehicle=self._vehicle_name)
            self._charging_session = None
        return new_state
