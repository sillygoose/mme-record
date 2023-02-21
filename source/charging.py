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
from logfiles import rollover


_LOGGER = logging.getLogger('mme')


class Charging:

    def __init__(self) -> None:
        self._charging_session = None
        self._exiting = False

    _requiredHashes = [
            Hash.HvbTemp, Hash.HvbEtE, Hash.HvbSoCD, Hash.HvbSoH,
            Hash.LvbSoC, Hash.LvbEnergy,
            Hash.ChargerInputEnergy
        ]

    def charge_starting(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Incoming:
            assert self._charging_session is None
            incoming_charge_time = int(time.time())
            self._charging_session = {
                'time':incoming_charge_time,
            }
            set_state(Hash.ChargerInputPowerMax, 0)
            set_state(Hash.ChargerOutputPowerMax, 0)
            _LOGGER.debug(f"Incoming charging session detected at {incoming_charge_time}")

        elif call_type == CallType.Outgoing:
            if self._exiting == False:
                for state in Charging._requiredHashes:
                    assert get_state_value(state, None) is not None, f"{state.name}"
                vehicleID = get_state_value(Hash.VehicleID)
                hvbSoCD = get_state_value(Hash.HvbSoCD)
                hvbTemp = get_state_value(Hash.HvbTemp)
                _LOGGER.info(f"Starting charging session in {vehicleID}, HVB SoC: {hvbSoCD}%, HVB temp: {hvbTemp}°C")
            else:
                self._charging_session = None
                self._exiting = False

        elif call_type == CallType.Default:
            if charging_status := get_ChargingStatus('charging_starting'):
                if charging_status not in [ChargingStatus.Charging, ChargingStatus.Ready]:
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
            if new_state != VehicleState.Unchanged:
                self._exiting = True

            for hash in Charging._requiredHashes:
                if (hash_value := get_state_value(hash, None)) is None:
                    arbitration_id, did_id, _ = get_hash_fields(hash)
                    _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: Waiting for required DID: '{hash.name}'")
                    return VehicleState.Unchanged
                self._charging_session[hash] = hash_value

            if charging_status := get_ChargingStatus('charging_starting'):
                if charging_status == ChargingStatus.Ready or charging_status == ChargingStatus.Wait or charging_status == ChargingStatus.Charging:
                    if charging_status == ChargingStatus.Charging:
                        if evse_type := get_EvseType('charging_starting'):
                            if evse_type == EvseType.BasAC:
                                new_state = VehicleState.Charge_AC
                                self._charging_session['type'] = 'AC'
                            elif evse_type != EvseType.NoType:
                                _LOGGER.error(f"While in '{VehicleState.Charge_Starting.name}', 'EvseType' returned an unexpected state: {evse_type}")
                else:
                    _LOGGER.info(f"While in {VehicleState.Charge_Starting.name}, 'ChargingStatus' returned an unexpected response: {charging_status}")
        return new_state

    def charge_ac(selff, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if charging_status := get_ChargingStatus('charging_ac'):
                if charging_status != ChargingStatus.Charging:
                    _LOGGER.debug(f"Charging status changed to: {charging_status}")
                    new_state = VehicleState.Charge_Ending
        return new_state

    def charge_dcfc(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Default:
            if charging_status := get_ChargingStatus('charging_dcfc'):
                if charging_status != ChargingStatus.Charging:
                    _LOGGER.debug(f"Charging status changed to: {charging_status}")
                    new_state = VehicleState.Charge_Ending
        return new_state

    def charge_ending(self, call_type: CallType) -> VehicleState:
        new_state = VehicleState.Unchanged
        if call_type == CallType.Incoming:
            return new_state

        elif call_type == CallType.Default:
            if not self.command_queue_empty():
                return new_state

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

        elif call_type == CallType.Outgoing:
            session = self._charging_session
            charger_type = set_state(Hash.CS_ChargerType, session.get('type'))
            starting_time = set_state(Hash.CS_TimeStart, session.get('time'))
            ending_time = set_state(Hash.CS_TimeEnd, int(time.time()))

            odometer = set_state(Hash.CS_Odometer, get_state_value(Hash.LoresOdometer))
            latitude = set_state(Hash.CS_Latitude, get_state_value(Hash.GpsLatitude))
            longitude = set_state(Hash.CS_Longitude, get_state_value(Hash.GpsLongitude))
            elevation = set_state(Hash.CS_Elevation, get_state_value(Hash.GpsElevation))
            max_input_power = set_state(Hash.CS_MaxInputPower, get_state_value(Hash.ChargerInputPowerMax))

            hvb_soh = set_state(Hash.CS_HvbSoH, session.get(Hash.HvbSoH))
            hvb_starting_temp = set_state(Hash.CS_HvbTempStart, session.get(Hash.HvbTemp))
            hvb_ending_temp = set_state(Hash.CS_HvbTempEnd, get_state_value(Hash.HvbTemp))
            hvb_starting_soc = set_state(Hash.CS_HvbSoCStart, session.get(Hash.HvbSoCD))
            hvb_ending_soc = set_state(Hash.CS_HvbSoCEnd, get_state_value(Hash.HvbSoCD))
            hvb_starting_ete = set_state(Hash.CS_HvbEtEStart, session.get(Hash.HvbEtE))
            hvb_ending_ete = set_state(Hash.CS_HvbEteEnd, get_state_value(Hash.HvbEtE))
            hvb_delta_energy = set_state(Hash.CS_HvbWhAdded, hvb_ending_ete - hvb_starting_ete)

            lvb_starting_soc = set_state(Hash.CS_LvbSoCStart, session.get(Hash.LvbSoC))
            lvb_ending_soc = set_state(Hash.CS_LvbSoCEnd, get_state_value(Hash.LvbSoC))
            lvb_delta_energy = set_state(Hash.CS_LvbWhAdded, get_state_value(Hash.LvbEnergy) - session.get(Hash.LvbEnergy))

            wh_added = set_state(Hash.CS_WhAdded, hvb_delta_energy + lvb_delta_energy)
            wh_used = set_state(Hash.CS_WhUsed, get_state_value(Hash.ChargerInputEnergy) - session.get(Hash.ChargerInputEnergy, 0.0))
            charging_efficiency = (set_state(Hash.CS_ChargingEfficiency, (wh_added / wh_used * 100.0) if wh_used > 0 else 0.0))
            session_datetime = datetime.datetime.fromtimestamp(starting_time).strftime('%Y-%m-%d %H:%M')
            hours, rem = divmod(ending_time - starting_time, 3600)
            minutes, _ = divmod(rem, 60)

            _LOGGER.info(f"{get_state_value(Hash.VehicleID)} charging session results:")
            _LOGGER.info(f"    {charger_type} charging session started at {session_datetime} for {hours} hours, {minutes} minutes")
            _LOGGER.info(f"    odometer: {odometer_km(odometer):.01f} km ({odometer_miles(odometer):.01f} mi)")
            _LOGGER.info(f"    starting HvB temperature: {hvb_starting_temp}°C, ending HvB temperature: {hvb_ending_temp}°C")
            _LOGGER.info(f"    starting HVB SoC: {hvb_starting_soc:.01f}%, ending SoC: {hvb_ending_soc:.01f}%")
            _LOGGER.info(f"    starting HVB EtE: {hvb_starting_ete} Wh, ending EtE: {hvb_ending_ete} Wh")
            _LOGGER.info(f"    HVB ΔWh: {hvb_delta_energy} Wh, LVB ΔWh: {lvb_delta_energy} Wh")
            _LOGGER.info(f"    starting LVB SoC: {lvb_starting_soc:.01f}%, ending SoC: {lvb_ending_soc:.01f}%")
            _LOGGER.info(f"    {wh_added} Wh were added, requiring {wh_used} Wh from the charger")
            _LOGGER.info(f"    overall efficiency: {charging_efficiency:.01f}%")
            _LOGGER.info(f"    maximum input power: {max_input_power} W")
            _LOGGER.info(f"    HVB state of health: {hvb_soh}%")

            if ending_time - starting_time >= self._minimum_charge:
                _LOGGER.info(f"    charging session timestamps: {get_state_value(Hash.CS_TimeStart)}   {get_state_value(Hash.CS_TimeEnd)}")
                tags = [Hash.Vehicle]
                fields = [
                        Hash.CS_TimeStart, Hash.CS_TimeEnd,
                        Hash.CS_Latitude, Hash.CS_Longitude, Hash.CS_Elevation, Hash.CS_Odometer,
                        Hash.CS_HvbTempStart, Hash.CS_HvbTempEnd,
                        Hash.CS_HvbSoCStart, Hash.CS_HvbSoCEnd, Hash.CS_HvbEtEStart, Hash.CS_HvbEteEnd,
                        Hash.CS_HvbWhAdded, Hash.CS_HvbSoH,
                        Hash.CS_WhAdded, Hash.CS_WhUsed, Hash.CS_ChargingEfficiency,
                        Hash.CS_MaxInputPower,
                        Hash.CS_ChargerType,
                    ]
                influxdb_charging(tags=tags, fields=fields, charge_start=Hash.CS_TimeStart)
                filename = 'charge_' + datetime.datetime.fromtimestamp(starting_time).strftime('%Y-%m-%d_%H_%M')
                self._file_manager.flush(filename)
                rollover(filename)
            self._charging_session = None
        return new_state
