"""
State definitions
"""
import logging
from threading import Lock
from queue import PriorityQueue
import json
import time
import datetime

from typing import List

from codec_manager import *
from did import KeyState, ChargingStatus, EvseType, GearCommanded, InferredKey
from did import EngineStartRemote, EngineStartNormal, EngineStartDisable, ChargePlugConnected
from state_engine import get_EngineStartDisable, get_state_value, set_state
from state_engine import get_EngineStartRemote, get_EngineStartNormal
from state_engine import get_EvseType, get_GearCommanded, get_ChargePlugConnected, get_ChargingStatus
from state_engine import get_InferredKey, get_KeyState
from hash import *
from synthetics import update_synthetics
from influxdb import influxdb_charging_session
from vehicle_state import VehicleState
from exceptions import RuntimeError


_LOGGER = logging.getLogger('mme')


class StateManager:

    _state_file_lookup = {
        VehicleState.Unknown:           {'state_file': 'json/state/unknown.json',           'state_keys': [Hash.InferredKey]},
        VehicleState.Off:               {'state_file': 'json/state/off.json',               'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected]},
        VehicleState.Accessory:         {'state_file': 'json/state/accessory.json',         'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected]},
        VehicleState.On:                {'state_file': 'json/state/on.json',                'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected, Hash.GearCommanded]},
        VehicleState.PluggedIn:         {'state_file': 'json/state/pluggedin.json',         'state_keys': [Hash.ChargePlugConnected, Hash.ChargingStatus]},
        VehicleState.Charging_AC:       {'state_file': 'json/state/charging_ac.json',       'state_keys': [Hash.ChargingStatus]},
        VehicleState.Charging_Starting: {'state_file': 'json/state/charging_starting.json', 'state_keys': [Hash.ChargingStatus]},
        VehicleState.Charging_Ended:    {'state_file': 'json/state/charging_ended.json',    'state_keys': [Hash.ChargingStatus]},
        VehicleState.Trip:              {'state_file': 'json/state/trip.json',              'state_keys': [Hash.GearCommanded]},
        ###
        VehicleState.Preconditioning:   {'state_file': 'json/state/preconditioning.json',   'state_keys': [Hash.ChargePlugConnected, Hash.ChargingStatus, Hash.EvseType]},
        VehicleState.Charging_DCFC:     {'state_file': 'json/state/charging_dcfc.json',     'state_keys': [Hash.ChargingStatus, Hash.EvseType]},
    }

    def __init__(self, config) -> None:
        self._vehicle_name = config.vehicle.name
        self._state = None
        self._charging_session = None
        self._putback_enabled = False
        self._codec_manager = CodecManager()
        self._command_queue = PriorityQueue()
        self._command_queue_lock = Lock()
        state_functions = {
            VehicleState.Unknown: self.unknown,
            VehicleState.Off: self.off,
            VehicleState.Accessory: self.accessory,
            VehicleState.On: self.on,
            VehicleState.Trip: self.trip,
            VehicleState.Preconditioning: self.preconditioning,
            VehicleState.PluggedIn: self.plugged_in,
            VehicleState.Charging_AC: self.charging_ac,
            VehicleState.Charging_DCFC: self.charging_dcfc,
            VehicleState.Charging_Starting: self.charging_starting,
            VehicleState.Charging_Ended: self.charging_ended,
        }
        assert len(state_functions) == len(StateManager._state_file_lookup)
        for k, v in StateManager._state_file_lookup.items():
            v['state_function'] = state_functions.get(k)

    def start(self) -> None:
        self.change_state(VehicleState.Unknown)

    def stop(self) -> None:
        pass

    def current_state(self) -> VehicleState:
        return self._state

    def _load_state_definition(self, file: str) -> List[dict]:
        with open(file) as infile:
            try:
                state_definition = json.load(infile)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"JSON error in '{file}' at line {e.lineno}")
            except FileNotFoundError as e:
                raise RuntimeError(f"{e}")

        for module in state_definition:
            dids = module.get('dids')
            for did in dids:
                codec_id = did.get('codec_id')
                codec = self._codec_manager.codec(codec_id)
                did['codec'] = codec
        return state_definition

    def _outgoing_state(self, state: VehicleState) -> None:
        if state == VehicleState.Charging_Ended:
            starting_time = self._charging_session.get('time')
            ending_time = int(time.time())
            duration_seconds = ending_time - starting_time
            starting_soc = self._charging_session.get(Hash.HvbSoC)
            starting_socd = self._charging_session.get(Hash.HvbSoCD)
            starting_ete = self._charging_session.get(Hash.HvbEtE)
            starting_charging_input_energy = self._charging_session.get(Hash.ChargerInputEnergy, 0.0)
            latitude = self._charging_session.get(Hash.GpsLatitude, 0.0)
            longitude = self._charging_session.get(Hash.GpsLongitude, 0.0)
            odometer = self._charging_session.get(Hash.LoresOdometer, 0)

            ending_soc = get_state_value(Hash.HvbSoC)
            ending_socd = get_state_value(Hash.HvbSoCD)
            ending_ete = get_state_value(Hash.HvbEtE)
            ending_charging_input_energy = get_state_value(Hash.ChargerInputEnergy)
            kwh_added = ending_ete - starting_ete
            kwh_used = (ending_charging_input_energy - starting_charging_input_energy) * 0.001
            charging_efficiency = kwh_added / kwh_used if kwh_used > 0 else 0.0
            session_datetime = datetime.datetime.fromtimestamp(starting_time).strftime('%Y-%m-%d %H:%M')
            hours, rem = divmod(duration_seconds, 3600)
            minutes, _ = divmod(rem, 60)
            charging_session = {
                'time':             starting_time,
                'duration':         duration_seconds,
                'location':         {'latitude': latitude, 'longitude': longitude},
                'odometer':         odometer,
                'soc':              {'starting': starting_soc, 'ending': ending_soc},
                'socd':             {'starting': starting_socd, 'ending': ending_socd},
                'ete':              {'starting': starting_ete, 'ending': ending_ete},
                'kwh_added':        kwh_added,
                'kwh_used':         kwh_used,
                'efficiency':       charging_efficiency,
            }
            _LOGGER.info(f"Charging session statistics:")
            _LOGGER.info(f"   session started at {session_datetime} for {hours} hours, {minutes} minutes")
            _LOGGER.info(f"   location was ({latitude:.05f},{longitude:.05f}), odometer is {odometer} km")
            _LOGGER.info(f"   starting SoC was {starting_socd:.01f}%, ending SoC was {ending_socd:.01f}%")
            _LOGGER.info(f"   starting EtE was {starting_ete:.03f} kWh, ending EtE was {ending_ete:.03f} kWh")
            _LOGGER.info(f"   {kwh_added:.03f} kWh were added, requiring {kwh_used:.03f} kWh from the AC charger")
            _LOGGER.info(f"   overall efficiency is {(charging_efficiency*100):.01f}%")
            influxdb_charging_session(session=charging_session, vehicle=self._vehicle_name)
            self._charging_session = None

    def _incoming_state(self, state: VehicleState) -> None:
        if state == VehicleState.Charging_Starting:
            self._charging_session = None

    def change_state(self, new_state: VehicleState) -> None:
        if self._state == new_state:
            return
        _LOGGER.info(f"Vehicle state changed from '{self._state.name}' to '{new_state.name}'" if self._state else f"Vehicle state set to '{new_state.name}'")

        self._putback_enabled = False
        self._flush_queue()

        self._outgoing_state(self._state)
        self._state = new_state
        self._state_time = time.time()
        self._state_file = StateManager._state_file_lookup.get(new_state).get('state_file')
        self._state_function = StateManager._state_file_lookup.get(new_state).get('state_function')
        self._queue_commands = self._load_state_definition(self._state_file)
        self._incoming_state(self._state)

    def _flush_queue(self) -> None:
        with self._command_queue_lock:
            while not self._command_queue.empty():
                self._command_queue.get_nowait()

    def _load_queue(self) -> None:
        with self._command_queue_lock:
            while not self._command_queue.empty():
                self._command_queue.get_nowait()
            for module in self._queue_commands:
                enable = module.get('enable', True)
                if enable:
                    period = module.get('period', 5)
                    offset = module.get('offset', 0)
                    payload = (time.time() + offset, period, [module])
                    self._command_queue.put(payload)
            self._putback_enabled = True

    def _get_state_keys(self) -> List[str]:
        return StateManager._state_file_lookup.get(self._state).get('state_keys')

    def update_vehicle_state(self, state_change: dict) -> List[dict]:
        state_data = []
        if state_change.get('type', None) is None:
            if did_id := state_change.get('did_id', None):
                codec = self._codec_manager.codec(did_id)
                decoded_payload = codec.decode(None, bytearray(state_change.get('payload')))
                arbitration_id = state_change.get('arbitration_id')
                states = decoded_payload.get('states')
                for state in states:
                    for state_name, state_value in state.items():
                        hash = get_hash(f"{arbitration_id:04X}:{did_id:04X}:{state_name}")
                        set_state(hash, state_value)
                        state_data.append({'arbitration_id': arbitration_id, 'did_id': did_id, 'name': state_name, 'value': state_value})
                        if synthetics := update_synthetics(hash):
                            state_data += synthetics
                return state_data

    def _update_state_machine(self) -> None:
        self._state_function()

    def unknown(self) -> None:
        # 'state_keys': [Hash.InferredKey]},
        for key in self._get_state_keys():
            if inferred_key := get_InferredKey(key, 'unknown'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'unknown'):
                        self.change_state(VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off)
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_disable := get_EngineStartDisable(Hash.EngineStartDisable, 'unknown'):
                        self.change_state(VehicleState.On if engine_start_disable == EngineStartDisable.No else VehicleState.Accessory)

    def off(self) -> None:
        # 'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected]},
        for key in self._get_state_keys():
            if inferred_key := get_InferredKey(key, 'off'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'off'):
                        if engine_start_remote == EngineStartRemote.Yes:
                            self.change_state(VehicleState.Preconditioning)
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'off'):
                        self.change_state(VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory)
            elif charge_plug_connected := get_ChargePlugConnected(key, 'off'):
                if charge_plug_connected == ChargePlugConnected.Yes:
                    self.change_state(VehicleState.PluggedIn)

    def accessory(self) -> None:
        # 'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected]},
        for key in self._get_state_keys():
            if inferred_key := get_InferredKey(key, 'accessory'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'accessory'):
                        self.change_state(VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off)
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'accessory'):
                        self.change_state(VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory)
            elif charge_plug_connected := get_ChargePlugConnected(key, 'accessory'):
                if charge_plug_connected == ChargePlugConnected.Yes:
                    self.change_state(VehicleState.PluggedIn)

    def on(self) -> None:
        # 'state_keys': [Hash.InferredKey, Hash.ChargePlugConnected, Hash.GearCommanded]},
        for key in self._get_state_keys():
            if inferred_key := get_InferredKey(key, 'on'):
                if inferred_key == InferredKey.KeyOut:
                    if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'on'):
                        self.change_state(VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off)
                elif inferred_key == InferredKey.KeyIn:
                    if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'on'):
                        self.change_state(VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory)
            elif charge_plug_connected := get_ChargePlugConnected(key, 'on'):
                if charge_plug_connected == ChargePlugConnected.Yes:
                    self.change_state(VehicleState.PluggedIn)
            elif gear_commanded := get_GearCommanded(key, 'on'):
                if gear_commanded != GearCommanded.Park:
                    self.change_state(VehicleState.Trip)

    def trip(self) -> None:
        # 'state_keys': [Hash.GearCommanded]},
        for key in self._get_state_keys():
            if gear_commanded := get_GearCommanded(key, 'trip'):
                if gear_commanded == GearCommanded.Park:
                    if inferred_key := get_InferredKey(Hash.InferredKey, 'trip'):
                        if inferred_key == InferredKey.KeyOut:
                            if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'trip'):
                                self.change_state(VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off)
                        elif inferred_key == InferredKey.KeyIn:
                            if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'trip'):
                                self.change_state(VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory)

    def preconditioning(self) -> None:
        for key in self._get_state_keys():
            if charging_status := get_ChargingStatus(key, 'preconditioning'):
                if charging_status == ChargingStatus.Charging:
                    pass
                elif charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Done:
                    if key_state := get_KeyState(Hash.KeyState, 'preconditioning'):
                        if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                            self.change_state(VehicleState.Off)
                        elif key_state == KeyState.On or key_state == KeyState.Cranking:
                            self.change_state(VehicleState.On)
                else:
                    _LOGGER.info(f"While {self._state}, 'ChargingStatus' returned an unexpected response: {charging_status}")
            elif remote_start := get_EngineStartRemote(key, 'preconditioning'):
                if remote_start == EngineStartRemote.No:
                    self.change_state(VehicleState.Unknown)

    def plugged_in(self) -> None:
        # 'state_keys': [Hash.ChargePlugConnected, Hash.ChargingStatus]},
        for key in self._get_state_keys():
            if charge_plug_connected := get_ChargePlugConnected(key, 'plugged_in'):
                if charge_plug_connected == ChargePlugConnected.No:
                    if inferred_key := get_InferredKey(Hash.InferredKey, 'plugged_in'):
                        if inferred_key == InferredKey.KeyOut:
                            if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'plugged_in'):
                                self.change_state(VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off)
                        elif inferred_key == InferredKey.KeyIn:
                            if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'plugged_in'):
                                self.change_state(VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory)
            elif charging_status := get_ChargingStatus(key, 'plugged_in'):
                if charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Wait:
                    pass
                elif charging_status == ChargingStatus.Ready or charging_status == ChargingStatus.Charging:
                    self.change_state(VehicleState.Charging_Starting)
                else:
                    _LOGGER.info(f"While in {self._state}, 'ChargingStatus' returned an unexpected response: {charging_status}")

    def charging_starting(self) -> None:
        if self._charging_session is None:
            self._charging_session = {
                'time': int(time.time()),
            }

        for key in self._get_state_keys():
            if charging_status := get_ChargingStatus(key, 'charging_starting'):
                if charging_status == ChargingStatus.Ready or charging_status == ChargingStatus.Wait or charging_status == ChargingStatus.Charging:
                    if self._charging_session.get(Hash.HvbEtE) is None:
                        if hvb_ete := get_state_value(Hash.HvbEtE, None):
                            self._charging_session[Hash.HvbEtE] = hvb_ete ###
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
                                self.change_state(VehicleState.Charging_AC)
                            elif evse_type != EvseType.NoType:
                                _LOGGER.error(f"While in '{self._state.name}', 'EvseType' returned an unexpected response: {evse_type}")
                else:
                    _LOGGER.info(f"While in {self._state}, 'ChargingStatus' returned an unexpected response: {charging_status}")

    def charging_ac(self) -> None:
        # 'state_keys': [Hash.ChargingStatus]},
        for key in self._get_state_keys():
            if charging_status := get_ChargingStatus(key, 'charging_ac'):
                if charging_status != ChargingStatus.Charging:
                    _LOGGER.debug(f"Charging status changed to: {charging_status}")
                    self.change_state(VehicleState.Charging_Ended)
                else:
                    assert get_state_value(Hash.HvbEtE, None) is not None
                    assert get_state_value(Hash.HvbSoC, None) is not None
                    assert get_state_value(Hash.HvbSoCD, None) is not None
                    ###assert get_state_value(Hash.GpsLatitude, None) is not None
                    ###assert get_state_value(Hash.GpsLongitude, None) is not None
                    assert get_state_value(Hash.LoresOdometer, None) is not None
                    assert get_state_value(Hash.ChargerInputEnergy, None) is not None
                    assert get_state_value(Hash.ChargerOutputEnergy, None) is not None


    def charging_ended(self) -> None:
        # 'state_keys': [Hash.ChargingStatus]},
        for key in self._get_state_keys():
            if charging_status := get_ChargingStatus(key, 'charging_ended'):
                if charging_status != ChargingStatus.Charging:
                    if charge_plug_connected := get_ChargePlugConnected(Hash.ChargePlugConnected, 'charging_ended'):
                        if charge_plug_connected == ChargePlugConnected.Yes:
                            self.change_state(VehicleState.PluggedIn)
                        elif inferred_key := get_InferredKey(Hash.InferredKey, 'charging_ended'):
                            if inferred_key == InferredKey.KeyOut:
                                if engine_start_remote := get_EngineStartRemote(Hash.EngineStartRemote, 'charging_ended'):
                                    self.change_state(VehicleState.Preconditioning if engine_start_remote == EngineStartRemote.Yes else VehicleState.Off)
                            elif inferred_key == InferredKey.KeyIn:
                                if engine_start_normal := get_EngineStartNormal(Hash.EngineStartNormal, 'charging_ended'):
                                    self.change_state(VehicleState.On if engine_start_normal == EngineStartNormal.Yes else VehicleState.Accessory)

    def charging_dcfc(self) -> None:
        for key in self._get_state_keys():
            if charging_status := get_ChargingStatus(key, 'charging_dcfc'):
                if charging_status == ChargingStatus.NotReady or charging_status == ChargingStatus.Done:
                    if key_state := get_KeyState(Hash.KeyState):
                        if key_state == KeyState.Sleeping or key_state == KeyState.Off:
                            self.change_state(VehicleState.Off)
                        elif key_state == KeyState.On or key_state == KeyState.Cranking:
                            self.change_state(VehicleState.On)
                else:
                    _LOGGER.info(f"While in '{self._state.name}', 'ChargingStatus' returned an unexpected response: {charging_status}")
