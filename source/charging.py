import logging
import time
import datetime

from state_engine import get_state_value, set_state, odometer_km, odometer_miles
from state_engine import get_ChargePlugConnected, get_ChargingStatus, get_EvseType
from state_engine import get_InferredKey, get_EngineStartRemote, get_EngineStartNormal

from did import ChargePlugConnected, ChargingStatus, EvseType
from did import InferredKey, EngineStartRemote, EngineStartNormal

from vehicle_state import VehicleState, CallType
from hash import *

from influxdb import influxdb_charging
from geocoding import reverse_geocode


_LOGGER = logging.getLogger('mme')


class Charging:

    def __init__(self) -> None:
        self._charging_session = None

    _requiredHashes = [
            Hash.LvbEnergy, Hash.HvbEtE, Hash.HvbSoCD,
            Hash.ChargerInputEnergy, Hash.ChargerOutputEnergy
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
            for state in Charging._requiredHashes:
                assert get_state_value(state, None) is not None, f"{state.name}"
            _LOGGER.info(f"Starting charging session, HVB SoC: {get_state_value(Hash.HvbSoCD)}%, HVB EtE: {get_state_value(Hash.HvbEtE)} Wh")

        elif call_type == CallType.Default:
            if charging_status := get_ChargingStatus('charging_starting'):
                if charging_status != ChargingStatus.Charging:
                    if charge_plug_connected := get_ChargePlugConnected('charging_starting'):
                        if charge_plug_connected == ChargePlugConnected.No:
                            new_state = VehicleState.Idle
                    if inferred_key := get_InferredKey('charging_starting'):
                        if inferred_key == InferredKey.KeyOut:
                            if engine_start_remote := get_EngineStartRemote('charging_starting'):
                                new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                        elif inferred_key == InferredKey.KeyIn:
                            if engine_start_normal := get_EngineStartNormal('charging_starting'):
                                new_state = VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory

            for hash in Charging._requiredHashes:
                if (hash_value := get_state_value(hash, None)) is None:
                    arbitration_id, did_id, _ = get_hash_fields(hash)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: Missing required DID: '{hash.name}'")
                    return new_state
                self._charging_session[hash] = hash_value

            if charging_status := get_ChargingStatus('charging_starting'):
                if charging_status == ChargingStatus.Ready or charging_status == ChargingStatus.Wait or charging_status == ChargingStatus.Charging:
                    if charging_status == ChargingStatus.Charging:
                        if evse_type := get_EvseType('charging_starting'):
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
            if charging_status := get_ChargingStatus('charging_ac'):
                if charging_status != ChargingStatus.Charging:
                    _LOGGER.debug(f"Charging status changed to: {charging_status}")
                    new_state = VehicleState.Charging_Ended
        return new_state

    def charging_dcfc(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if charging_status := get_ChargingStatus('charging_dcfc'):
                if charging_status != ChargingStatus.Charging:
                    _LOGGER.debug(f"Charging status changed to: {charging_status}")
                    new_state = VehicleState.Charging_Ended
        return new_state

    def charging_ended(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Outgoing:
            pass

        elif call_type == CallType.Default:
            if charging_status := get_ChargingStatus('charging_ended'):
                if charging_status != ChargingStatus.Charging:
                    if charge_plug_connected := get_ChargePlugConnected('charging_ended'):
                        if charge_plug_connected == ChargePlugConnected.Yes:
                            new_state = VehicleState.PluggedIn
                        elif inferred_key := get_InferredKey('charging_ended'):
                            if inferred_key == InferredKey.KeyOut:
                                if engine_start_remote := get_EngineStartRemote('charging_ended'):
                                    new_state = VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Idle
                            elif inferred_key == InferredKey.KeyIn:
                                if engine_start_normal := get_EngineStartNormal('charging_ended'):
                                    new_state = VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory

        elif call_type == CallType.Incoming:
            session = self._charging_session
            vehicle = set_state(Hash.Vehicle, self._vehicle_name)
            charger_type = set_state(Hash.CS_ChargerType, session.get('type'))
            starting_time = set_state(Hash.CS_TimeStart, session.get('time'))
            ending_time = set_state(Hash.CS_TimeEnd, int(time.time()))
            starting_socd = set_state(Hash.CS_StartSoCD, session.get(Hash.HvbSoCD))
            ending_socd = set_state(Hash.CS_EndSoCD, get_state_value(Hash.HvbSoCD))
            starting_ete = set_state(Hash.CS_StartEtE, session.get(Hash.HvbEtE))
            ending_ete = set_state(Hash.CS_EndEte, get_state_value(Hash.HvbEtE))
            odometer = set_state(Hash.CS_Odometer, get_state_value(Hash.LoresOdometer))
            latitude = set_state(Hash.CS_Latitude, get_state_value(Hash.GpsLatitude))
            longitude = set_state(Hash.CS_Longitude, get_state_value(Hash.GpsLongitude))
            max_input_power = set_state(Hash.CS_MaxInputPower, get_state_value(Hash.ChargerInputPowerMax))

            delta_lvb_energy = get_state_value(Hash.LvbEnergy) - session.get(Hash.LvbEnergy)
            delta_hvb_energy = ending_ete - starting_ete
            wh_added = set_state(Hash.CS_WhAdded, int(delta_hvb_energy + delta_lvb_energy))
            wh_used = set_state(Hash.CS_WhUsed, int(get_state_value(Hash.ChargerInputEnergy) - session.get(Hash.ChargerInputEnergy, 0.0)))
            charging_efficiency = (set_state(Hash.CS_ChargingEfficiency, wh_added / wh_used * 100.0) if wh_used > 0 else 0.0)
            session_datetime = datetime.datetime.fromtimestamp(starting_time).strftime('%Y-%m-%d %H:%M')
            hours, rem = divmod(ending_time - starting_time, 3600)
            minutes, _ = divmod(rem, 60)

            _LOGGER.info(f"'{vehicle}' charging session results:")
            _LOGGER.info(f"    {charger_type} charging session started at {session_datetime} for {hours} hours, {minutes} minutes")
            _LOGGER.info(f"    odometer: {odometer_km(odometer):.01f} km ({odometer_miles(odometer):.01f} mi)")
            _LOGGER.info(f"    location: {reverse_geocode(latitude, longitude)}")
            _LOGGER.info(f"    starting SoC: {starting_socd:.01f}%, ending SoC: {ending_socd:.01f}%")
            _LOGGER.info(f"    starting EtE: {starting_ete} Wh, ending EtE: {ending_ete} Wh, LVB ΔWh: {delta_lvb_energy} Wh")
            _LOGGER.info(f"    {wh_added} Wh were added, requiring {wh_used} Wh from the charger")
            _LOGGER.info(f"    overall efficiency: {charging_efficiency:.01f}%")
            _LOGGER.info(f"    maximum input power: {max_input_power} W")

            tags = [Hash.CS_ChargerType, Hash.Vehicle]
            fields = [
                    Hash.CS_TimeStart, Hash.CS_TimeEnd,
                    Hash.CS_Latitude, Hash.CS_Longitude, Hash.CS_Odometer,
                    Hash.CS_StartSoCD, Hash.CS_EndSoCD, Hash.CS_StartEtE, Hash.CS_EndEte,
                    Hash.CS_WhAdded, Hash.CS_WhUsed, Hash.CS_ChargingEfficiency, Hash.CS_MaxInputPower,
                ]
            influxdb_charging(tags=tags, fields=fields, charge_start=Hash.CS_TimeStart)
            self._charging_session = None
        return new_state
