import logging
import time
import datetime

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

    _requiredStates = [
            Hash.LvbEnergy, Hash.LoresOdometer, Hash.HvbEtE, Hash.HvbSoC, Hash.HvbSoCD,
            Hash.GpsLatitude, Hash.GpsLongitude, Hash.ChargerInputEnergy, Hash.ChargerOutputEnergy
        ]

    def charging_starting(self,call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Incoming:
            assert self._charging_session is None
            self._charging_session = {
                'time': int(time.time()),
            }
            set_state(Hash.ChargerInputPowerMax, 0)
            set_state(Hash.ChargerOutputPowerMax, 0)

        elif call_type == CallType.Outgoing:
            for state in Charging._requiredStates:
                assert get_state_value(state, None) is not None

        elif call_type == CallType.Default:
            if charging_status := get_ChargingStatus(Hash.ChargingStatus, 'charging_starting'):
                if charging_status != ChargingStatus.Charging:
                    if charge_plug_connected := get_ChargePlugConnected(Hash.ChargePlugConnected, 'charging_starting'):
                        if charge_plug_connected == ChargePlugConnected.No:
                            new_state = VehicleState.Idle
                    if inferred_key := get_InferredKey(Hash.InferredKey, 'charging_starting'):
                        if inferred_key == InferredKey.KeyOut:
                            if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'charging_starting'):
                                new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                        elif inferred_key == InferredKey.KeyIn:
                            if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'charging_starting'):
                                new_state = VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory

            for state in Charging._requiredStates:
                if (state_value := get_state_value(state, None)) is None:
                    return new_state
                self._charging_session[state] = state_value

            if charging_status := get_ChargingStatus(Hash.ChargingStatus, 'charging_starting'):
                if charging_status == ChargingStatus.Ready or charging_status == ChargingStatus.Wait or charging_status == ChargingStatus.Charging:
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

    def charging_ac(selff, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if charging_status := get_ChargingStatus(Hash.ChargingStatus, 'charging_ac'):
                if charging_status != ChargingStatus.Charging:
                    _LOGGER.debug(f"Charging status changed to: {charging_status}")
                    new_state = VehicleState.Charging_Ended
        return new_state

    def charging_dcfc(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if charging_status := get_ChargingStatus(Hash.ChargingStatus, 'charging_dcfc'):
                if charging_status != ChargingStatus.Charging:
                    _LOGGER.debug(f"Charging status changed to: {charging_status}")
                    new_state = VehicleState.Charging_Ended
        return new_state

    def charging_ended(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Outgoing:
            pass

        elif call_type == CallType.Default:
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

        elif call_type == CallType.Incoming:
            session = self._charging_session
            charger_type = session.get('type')
            starting_time = session.get('time')
            ending_time = int(time.time())
            starting_soc = session.get(Hash.HvbSoC)
            starting_socd = session.get(Hash.HvbSoCD)
            starting_ete = session.get(Hash.HvbEtE)
            starting_charging_input_energy = session.get(Hash.ChargerInputEnergy, 0.0)
            starting_lvb_energy = session.get(Hash.LvbEnergy)
            latitude = session.get(Hash.GpsLatitude, 0.0)
            longitude = session.get(Hash.GpsLongitude, 0.0)
            odometer = session.get(Hash.LoresOdometer, 0)

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
            hours, rem = divmod(ending_time - starting_time, 3600)
            minutes, _ = divmod(rem, 60)
            charging_session = {
                'type':             charger_type,
                'time':             {'starting': starting_time, 'ending': ending_time},
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
            _LOGGER.info(f"    location: {reverse_geocode(latitude, longitude)}")
            _LOGGER.info(f"    starting SoC: {starting_socd:.01f}%, ending SoC: {ending_socd:.01f}%")
            _LOGGER.info(f"    starting EtE: {starting_ete:.0f} Wh, ending EtE: {ending_ete:.0f} Wh, LVB delta energy: {delta_lvb_energy:.0f} Wh")
            _LOGGER.info(f"    {wh_added:.0f} Wh were added, requiring {wh_used:.0f} Wh from the charger")
            _LOGGER.info(f"    overall efficiency: {(charging_efficiency*100):.01f}%")
            _LOGGER.info(f"    maximum input power: {max_input_power:.0f} W")
            influxdb_charging_session(session=charging_session, vehicle=self._vehicle_name)
            self._charging_session = None
        return new_state
