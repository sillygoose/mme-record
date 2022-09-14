import logging
import struct

import requests
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout, HTTPError, InvalidURL
from requests.exceptions import InvalidSchema, MissingSchema

from udsoncan import DidCodec

from did import DidId
from config.configuration import Configuration

from state_engine import odometer_km, odometer_miles, speed_kph, speed_mph


_LOGGER = logging.getLogger('mme')


class Codec(DidCodec):
    def encode(self, val):
        return val


class CodecNull(Codec):
    def decode(self, payload):
        payload_list = list(payload)
        decoded_str = str(payload_list) + f" {[hex(x) for x in payload_list]}"
        return {'payload': payload, 'states': [], 'decoded': decoded_str}

    def __len__(self):
        raise Codec.ReadAllRemainingData


class CodecKeyState(Codec):
    def decode(self, payload):
        key_state = struct.unpack('>B', payload)[0]
        key_states = {0: 'Sleeping', 3: 'On', 4: 'Starting', 5: 'Off'}
        state_string = 'Key state: ' + key_states.get(key_state, f"unknown ({key_state})")
        states = [{'key_state': key_state}]
        return {'payload': payload, 'states': states, 'decoded': state_string}

    def __len__(self):
        return 1


class CodecInferredKey(Codec):
    def decode(self, payload):
        inferred_key = struct.unpack('>B', payload)[0]
        inferred_key_states = {0: 'Unknown', 1: 'Key In', 2: 'Key Out'}
        state_string = 'Inferred key state: ' + inferred_key_states.get(inferred_key, f"unknown ({inferred_key})")
        states = [{'inferred_key': inferred_key}]
        return {'payload': payload, 'states': states, 'decoded': state_string}

    def __len__(self):
        return 1


class CodecEngineRunTime(Codec):
    def decode(self, payload):
        engine_runtime = struct.unpack('>H', payload)[0]
        states = [{'engine_runtime': engine_runtime}]
        return {'payload': payload, 'states': states, 'decoded': f"Engine run time: {engine_runtime} s"}

    def __len__(self):
        return 2


class CodecEngineStart(Codec):
    def decode(self, payload):
        engine_start = struct.unpack_from('>L', payload, offset=0)[0]
        engine_start_normal = bool(engine_start & 0x80000000)
        engine_start_remote = bool(engine_start & 0x40000000)
        engine_start_disable = bool(engine_start & 0x20000000)
        engine_start_extended = bool(engine_start & 0x00800000)
        states = [
            {'engine_start_normal': engine_start_normal},
            {'engine_start_disable': engine_start_disable},
            {'engine_start_remote': engine_start_remote},
            {'engine_start_extended': engine_start_extended},
        ]
        return {'payload': payload, 'states': states, 'decoded': f"Start engine bit field ({engine_start:08X}): normal={engine_start_normal}, remote={engine_start_remote}, disable={engine_start_disable}"}

    def __len__(self):
        return 4


class CodecChargePlug(Codec):
    def decode(self, payload):
        charge_plug = struct.unpack_from('>L', payload, offset=0)[0]
        charge_plug_connected = bool(charge_plug & 0x00004000)
        states = [
            {'charge_plug_connected': charge_plug_connected},
        ]
        return {'payload': payload, 'states': states, 'decoded': f"Charge plug bit field ({charge_plug:08X}): charge_plug_connected={charge_plug_connected}"}

    def __len__(self):
        return 4


class CodecGearDisplayed(Codec):
    def decode(self, payload):
        gear_displayed = struct.unpack('>B', payload)[0]
        gears = {0: 'Park', 1: 'Reverse', 2: 'Neutral', 3: 'Drive', 4: 'Low'}
        gear_string = 'Gear displayed: ' + gears.get(gear_displayed, 'Unknown')
        states = [{'gear_displayed': gear_displayed}]
        return {'payload': payload, 'states': states, 'decoded': gear_string}

    def __len__(self):
        return 1


class CodecGearCommanded(Codec):
    def decode(self, payload):
        gear_commanded = struct.unpack('>B', payload)[0]
        gears = {70: 'Park', 60: 'Reverse', 50: 'Neutral', 40: 'Drive', 20: 'Low', 255: 'Fault'}
        gear = 'Gear selected: ' + gears.get(gear_commanded, 'Unknown')
        states = [{'gear_commanded': gear_commanded}]
        return {'payload': payload, 'states': states, 'decoded': gear}

    def __len__(self):
        return 1


class CodecGPS(Codec):
    """
    _previous_gps_speed = -1
    """

    def decode(self, payload):
        # default to using MME GPS data
        gps_elevation, gps_latitude, gps_longitude, gps_fix, gps_speed, gps_bearing = struct.unpack('>hllBHH', payload)

        if gps_fix == 255:
            # saved hires GPS data vi playback
            gps_elevation, gps_latitude, gps_longitude, gps_fix, gps_speed, gps_bearing = struct.unpack('>hffBHH', payload)
            gps_speed *= 3.6
            states = [
                    {'gps_latitude': gps_latitude},
                    {'gps_longitude': gps_longitude},
                    {'gps_elevation': gps_elevation},
                    {'gps_speed': gps_speed},
                    {'gps_bearing': gps_bearing},
                ]
            gps_data = f"GPS: ({gps_latitude:3.6f}, {gps_longitude:3.6f}), elevation: {gps_elevation} m, bearing: {gps_bearing}°, speed: {gps_speed:.01f} kph, fix: {gps_fix}"

            """
            if self != 'pb':
                if CodecGPS._previous_gps_speed == 0:
                    if gps_speed == 0:
                        _LOGGER.debug(f"07D0/8012: Discarding precise: {gps_data}")
                        return None
                CodecGPS._previous_gps_speed = gps_speed
            """

        else:
            # vehicle lores GPS data
            gps_latitude = float(gps_latitude / 60.0)
            gps_longitude = float(gps_longitude / 60.0)
            gps_speed *= 3.6
            states = [
                    {'gps_latitude': gps_latitude},
                    {'gps_longitude': gps_longitude},
                    {'gps_elevation': gps_elevation},
                    {'gps_speed': gps_speed},
                    {'gps_bearing': gps_bearing},
                ]
            gps_data = f"GPS: ({gps_latitude:3.6f}, {gps_longitude:3.6f}), elevation: {gps_elevation} m, bearing: {gps_bearing}°, speed: {gps_speed:.01f} kph, fix: {gps_fix}"

            """
            if self != 'pb':
                if CodecGPS._previous_gps_speed == 0:
                    if gps_speed == 0:
                        _LOGGER.debug(f"07D0/8012: Discarding MME: {gps_data}")
                        return None
                CodecGPS._previous_gps_speed = gps_speed
            """

            # Use the external GPS server if available
            if CodecManager._gps_server_enabled:
                # if successful modify the payload to reflect the hires GPS data
                try:
                    gps_response = requests.get(CodecManager._gps_server, timeout=CodecManager._gps_server_timeout)
                    phone_gps = gps_response.json()
                    gps_latitude = round(float(phone_gps.get('latitude')), 6)
                    gps_longitude = round(float(phone_gps.get('longitude')), 6)
                    gps_elevation = int(phone_gps.get('altitude'))

                    jps_speed = phone_gps.get('speed')
                    if jps_speed >= 0.0:
                        gps_speed = int(jps_speed)
                        gps_speed *= 3.6

                    jps_bearing = phone_gps.get('course')
                    if jps_bearing >= 0.0:
                        gps_bearing = int(jps_bearing)

                    gps_elapsed = gps_response.elapsed.seconds + round(gps_response.elapsed.microseconds/1000000, 3)
                    states = [
                            {'gps_latitude': gps_latitude},
                            {'gps_longitude': gps_longitude},
                            {'gps_elevation': gps_elevation},
                        ]
                    if gps_speed >= 0.0:
                        states.append({'gps_speed': gps_speed})
                    if gps_bearing >= 0.0:
                        states.append({'gps_bearing': gps_bearing})

                    gps_data = f"GPS: ({gps_latitude:3.6f}, {gps_longitude:3.6f}), elevation: {gps_elevation} m, bearing: {gps_bearing}°, speed: {gps_speed:.01f} kph, elapsed: {gps_elapsed:.03f}"
                    payload = struct.pack('>hffBHH', int(gps_elevation), float(gps_latitude), float(gps_longitude), 255, int(gps_speed / 3.6), int(gps_bearing))
                    return {'payload': payload, 'states': states, 'decoded': gps_data}
                except (ReadTimeout, HTTPError, InvalidURL, InvalidSchema, ConnectTimeout, ConnectionError) as e:
                    _LOGGER.error(f"{e}")
                    return None
                except Exception as e:
                    _LOGGER.exception(f"Unexpected GPS exception: {e}")
            else:
                if self != 'pb':
                    CodecManager._gps_server_enabled = connect_gps_server()


        return {'payload': payload, 'states': states, 'decoded': gps_data}

    def __len__(self):
        return 15


class CodecLoresOdometer(Codec):
    def decode(self, payload):
        odometer_high, odometer_low = struct.unpack('>HB', payload)
        lores_odometer = float(odometer_high * 256 + odometer_low)
        states = [{'lores_odometer': lores_odometer}]
        return {'payload': payload, 'states': states, 'decoded': f"Lores odometer: {odometer_km(lores_odometer):.01f} km ({odometer_miles(lores_odometer):.01f} mi)"}

    def __len__(self):
        return 3


class CodecHiresOdometer(Codec):
    def decode(self, payload):
        odometer_high, odometer_low = struct.unpack('>HB', payload)
        hires_odometer = float(odometer_high * 256 + odometer_low) * 0.1
        states = [{'hires_odometer': hires_odometer}]
        return {'payload': payload, 'states': states, 'decoded': f"Hires odometer: {odometer_km(hires_odometer):.01f} km ({odometer_miles(hires_odometer):.01f} mi)"}

    def __len__(self):
        return 3


class CodecHiresSpeed(Codec):
    def decode(self, payload):
        hires_speed = struct.unpack('>H', payload)[0]
        hires_speed = hires_speed / 128.0
        states = [{'hires_speed': hires_speed}]
        return {'payload': payload, 'states': states, 'decoded': f"Hires Speed: {speed_kph(hires_speed):.01f} kph ({speed_mph(hires_speed):.01f} mph)"}

    def __len__(self):
        return 2


class CodecExteriorTemp(Codec):
    def decode(self, payload):
        exterior_temp = struct.unpack('>B', payload)[0] - 40
        states = [{'exterior_temp': exterior_temp}]
        return {'payload': payload, 'states': states, 'decoded': f"Exterior temperature: {exterior_temp}°C"}

    def __len__(self):
        return 1


class CodecInteriorTemp(Codec):
    def decode(self, payload):
        interior_temp = struct.unpack('>B', payload)[0] - 40
        states = [{'interior_temp': interior_temp}]
        return {'payload': payload, 'states': states, 'decoded': f"Interior temperature: {interior_temp}°C"}

    def __len__(self):
        return 1


class CodecTime(Codec):
    def decode(self, payload):
        car_time = struct.unpack('>L', payload)[0] * 0.1
        states = [{'time': car_time}]
        return {'payload': payload, 'states': states, 'decoded': f"MME time: {car_time:.1f} s"}

    def __len__(self):
        return 4


class CodecHvbSoc(Codec):
    def decode(self, payload):
        hvb_soc = struct.unpack('>H', payload)[0] * 0.002
        states = [{'hvb_soc': hvb_soc}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB internal SoC: {hvb_soc:.3f}%"}

    def __len__(self):
        return 2


class CodecHvbSocD(Codec):
    def decode(self, payload):
        hvb_socd = float(struct.unpack('>B', payload)[0]) * 0.5
        states = [{'hvb_socd': hvb_socd}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB SoC: {hvb_socd:.01f}%"}

    def __len__(self):
        return 1


class CodecHvbEtE(Codec):
    def decode(self, payload):
        hvb_ete = struct.unpack('>H', payload)[0] * 2
        states = [{'hvb_ete': hvb_ete}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB energy to empty: {hvb_ete:.0f} Wh"}

    def __len__(self):
        return 2


class CodecHvbTemp(Codec):
    def decode(self, payload):
        hvb_temp = struct.unpack('>B', payload)[0] - 50
        states = [{'hvb_temp': hvb_temp}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB temperature: {hvb_temp}°C"}

    def __len__(self):
        return 1


class CodecHvbCHP(Codec):
    # INT16(A:B)×.001
    def decode(self, payload):
        hvb_chp = struct.unpack('>H', payload)[0] * 0.001
        states = [{'hvb_chp': hvb_chp}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB coolant heater power: {hvb_chp} W"}

    def __len__(self):
        return 2


class CodecHvbCHOp(Codec):
    # LOOKUP(A:A:0='Off':1='On':2='Dgrd':3='Shut':4='Shrt':5='NRes':6='?':7='Stop')
    def decode(self, payload):
        hvb_chop = struct.unpack('>B', payload)[0]
        hvb_chop_options = {0: 'Off', 1: 'On', 2: 'Dgrd', 3: 'Shut', 4: 'Shrt', 5: 'NRes', 7: 'Stop'}
        coolant_heating_mode = 'HVB coolant heating mode: ' + hvb_chop_options.get(hvb_chop, 'Unknown')
        states = [{'hvb_chop': hvb_chop}]
        return {'payload': payload, 'states': states, 'decoded': coolant_heating_mode}

    def __len__(self):
        return 1


class CodecLvbSoc(Codec):
    def decode(self, payload):
        lvb_soc = float(struct.unpack('>B', payload)[0])
        states = [{'lvb_soc': lvb_soc}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB SoC: {lvb_soc:.0f}%"}

    def __len__(self):
        return 1


class CodecLvbVoltage(Codec):
    def decode(self, payload):
        lvb_voltage = struct.unpack('>B', payload)[0] * 0.05 + 6.0
        states = [{'lvb_voltage': lvb_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB voltage: {lvb_voltage:.01f} V"}

    def __len__(self):
        return 1

class CodecLvbCurrent(Codec):
    def decode(self, payload):
        lvb_current = struct.unpack('>B', payload)[0] - 127
        states = [{'lvb_current': lvb_current}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB current: {lvb_current} A"}

    def __len__(self):
        return 1


class CodecHvbVoltage(Codec):
    def decode(self, payload):
        hvb_voltage = struct.unpack('>H', payload)[0] * 0.01
        states = [{'hvb_voltage': hvb_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB voltage: {hvb_voltage:.2f} V"}

    def __len__(self):
        return 2


class CodecHvbCurrent(Codec):
    def decode(self, payload):
        current_msb, current_lsb = struct.unpack('>bB', payload)
        hvb_current = (current_msb * 256 + current_lsb) * 0.1
        states = [{'hvb_current': hvb_current}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB current: {hvb_current:.1f} A"}

    def __len__(self):
        return 2


class CodecChargingStatus(Codec):
    def decode(self, payload):
        charging_status = struct.unpack('>B', payload)[0]
        charging_statuses = {
            0: 'Not Ready', 1: 'Wait', 2: 'Ready', 3: 'Charging', 4: 'Done', 5: 'Fault',
        }
        status_string = 'Charging status: ' + charging_statuses.get(charging_status, f"unknown ({charging_status})")
        states = [{'charging_status': charging_status}]
        return {'payload': payload, 'states': states, 'decoded': status_string}

    def __len__(self):
        return 1


class CodecChargerStatus(Codec):
    def decode(self, payload):
        charger_status = struct.unpack('>B', payload)[0]
        charger_statuses = {
            0: 'Not Ready', 1: 'Ready', 2: 'Fault', 3: 'WChk', 4: 'PreC', 5: 'Charging',
            6: 'Done', 7: 'ExtC', 8: 'Init',
        }
        status_string = 'Charger status: ' + charger_statuses.get(charger_status, f"unknown ({charger_status})")
        states = [{'charger_status': charger_status}]
        return {'payload': payload, 'states': states, 'decoded': status_string}

    def __len__(self):
        return 1


class CodecEvseType(Codec):
    def decode(self, payload):
        evse_type = struct.unpack('>B', payload)[0]
        evse_types = {
            0: 'None', 1: 'Level 1', 2: 'Level 2', 3: 'DC', 4: 'Bas', 5: 'HL',
            6: 'BasAC', 7: 'HLAC', 8: 'HLDC', 9: 'Unknown', 10: 'NCom',
            11: 'FAULT', 12: 'HEnd'
        }
        type_string = 'EVSE type: ' + evse_types.get(evse_type, f"unknown ({evse_type})")
        states = [{'evse_type': evse_type}]
        return {'payload': payload, 'states': states, 'decoded': type_string}

    def __len__(self):
        return 1


class CodecEvseDigitalMode(Codec):
    def decode(self, payload):
        evse_digital_mode = struct.unpack('>B', payload)[0]
        digital_modes = { 0: 'None', 1: 'DCE-', 2: 'DC-P', 3: 'DCEP', 4: 'ACE-', 5: 'AC-P', 6: 'ACEP', 7: 'Rst', 8: 'Off', 9: 'Est', 10: 'FAIL' }
        mode = digital_modes.get(evse_digital_mode, f"unknown ({evse_digital_mode})")
        states = [{'evse_digital_mode': evse_digital_mode}]
        return {'payload': payload, 'states': states, 'decoded': ('EVSE digital mode: ' + mode)}

    def __len__(self):
        return 1


class CodecHvbSoH(Codec):
    def decode(self, payload):
        hvb_soh = float(struct.unpack('>B', payload)[0]) * 0.5
        states = [{'hvb_soh': hvb_soh}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB SoH: {hvb_soh:.1f}%"}

    def __len__(self):
        return 1


class CodecChargerInputVoltage(Codec):
    def decode(self, payload):
        charger_input_voltage = struct.unpack('>H', payload)[0] * 0.01
        states = [{'charger_input_voltage': charger_input_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger input voltage: {charger_input_voltage:.1f} V"}

    def __len__(self):
        return 2


class CodecChargerInputCurrent(Codec):
    def decode(self, payload):
        charger_input_current = struct.unpack('>B', payload)[0]
        states = [{'charger_input_current': charger_input_current}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger input current: {charger_input_current} A"}

    def __len__(self):
        return 1


class CodecChargerInputFrequency(Codec):
    def decode(self, payload):
        charger_input_frequency = struct.unpack('>B', payload)[0] * 0.5
        states = [{'charger_input_frequency': charger_input_frequency}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger input frequency: {charger_input_frequency:.1f} Hz"}

    def __len__(self):
        return 1


class CodecChargerPilotVoltage(Codec):
    def decode(self, payload):
        charger_pilot_voltage = struct.unpack('>B', payload)[0] * 0.1
        states = [{'charger_pilot_voltage': charger_pilot_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger pilot voltage: {charger_pilot_voltage:.1f} V"}

    def __len__(self):
        return 1


class CodecChargerPilotDutyCycle(Codec):
    def decode(self, payload):
        charger_pilot_duty_cycle = struct.unpack('>B', payload)[0] * 0.5
        states = [{'charger_pilot_duty_cycle': charger_pilot_duty_cycle}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger pilot duty cycle: {charger_pilot_duty_cycle:.1f}"}

    def __len__(self):
        return 1


class CodecChargerInputPowerAvailable(Codec):
    def decode(self, payload):
        charger_input_power_available = struct.unpack('>h', payload)[0] * 0.005
        states = [{'charger_input_power_available': charger_input_power_available}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger input power available: {charger_input_power_available:.1f} kW"}

    def __len__(self):
        return 2


class CodecChargerMaxPower(Codec):
    def decode(self, payload):
        charger_max_power = struct.unpack('>H', payload)[0] * 0.05
        states = [{'charger_max_power': charger_max_power}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger maximum power: {charger_max_power:.3f} kW"}

    def __len__(self):
        return 2


class CodecChargerOutputVoltage(Codec):
    def decode(self, payload):
        charger_output_voltage = struct.unpack('>H', payload)[0] * 0.01
        states = [{'charger_output_voltage': charger_output_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger output voltage: {charger_output_voltage:.1f} V"}

    def __len__(self):
        return 2


class CodecChargerOutputCurrent(Codec):
    def decode(self, payload):
        charger_output_current = struct.unpack('>h', payload)[0] * 0.01
        states = [{'charger_output_current': charger_output_current}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger output current: {charger_output_current:.1f} A"}

    def __len__(self):
        return 2


class CodecChargerPowerLimit(Codec):
    def decode(self, payload):
        charger_power_limit = struct.unpack('>h', payload)[0] * 0.1
        states = [{'charger_power_limit': charger_power_limit}]
        return {'payload': payload, 'states': states, 'decoded': f"Charge power limit: {charger_power_limit:.1f} A"}

    def __len__(self):
        return 2


class CodecHvbChargeCurrentRequested(Codec):
    def decode(self, payload):
        hvb_charge_current_requested = struct.unpack('>h', payload)[0] * 0.01
        states = [{'hvb_charge_current_requested': hvb_charge_current_requested}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB charge current requested: {hvb_charge_current_requested:.1f} A"}

    def __len__(self):
        return 2


class CodecHvbChargeVoltageRequested(Codec):
    def decode(self, payload):
        hvb_charge_voltage_requested = struct.unpack('>B', payload)[0] * 2
        states = [{'hvb_charge_voltage_requested': hvb_charge_voltage_requested}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB charge voltage requested: {hvb_charge_voltage_requested} V"}

    def __len__(self):
        return 1


class CodecHvbMaxChargeCurrent(Codec):
    def decode(self, payload):
        hvb_max_charge_current = struct.unpack('>h', payload)[0] * 0.05
        states = [{'hvb_max_charge_current': hvb_max_charge_current}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB maximum charge current: {hvb_max_charge_current:.1f} A"}

    def __len__(self):
        return 2


class CodecLvbDcDcEnable(Codec):
    def decode(self, payload):
        lvb_dcdc = struct.unpack('>H', payload)[0]
        lvb_dcdc_enable = bool(lvb_dcdc & 0x0100)
        states = [{'lvb_dcdc_enable': lvb_dcdc_enable}]
        return {'payload': payload, 'states': states, 'decoded': f"DC-DC bit field ({lvb_dcdc:04X}): lvb_dcdc_enable={lvb_dcdc_enable}"}

    def __len__(self):
        return 2


class CodecLvbDcDcHVCurrent(Codec):
    def decode(self, payload):
        lvb_dcdc_hv_current = struct.unpack('>B', payload)[0] * 0.1
        states = [{'lvb_dcdc_hv_current': lvb_dcdc_hv_current}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB DC-DC HV current: {lvb_dcdc_hv_current:.1f} A"}

    def __len__(self):
        return 1


class CodecLvbDcDcLVCurrent(Codec):
    def decode(self, payload):
        lvb_dcdc_lv_current = struct.unpack('>B', payload)[0]
        states = [{'lvb_dcdc_lv_current': lvb_dcdc_lv_current}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB DC-DC LV current: {lvb_dcdc_lv_current} A"}

    def __len__(self):
        return 1


class CodecHvbContactorStatus(Codec):
    def decode(self, payload):
        contactor_status = struct.unpack_from('>L', payload, offset=0)[0]
        states = [{'hvb_contactor_status': contactor_status}]
        return {'payload': payload, 'states': states, 'decoded': f"Contactor status: {contactor_status:08X}"}

    def __len__(self):
        return 4


class CodecHvbContactorPositiveLeakVoltage(Codec):
    def decode(self, payload):
        raw_data = struct.unpack('>H', payload)[0]
        leak_voltage = float(raw_data) * 0.001
        states = [{'hvb_contactor_positive_leak_voltage': leak_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"Positive Contactor Leak Voltage: {leak_voltage:.01f} V ({raw_data:04X})"}

    def __len__(self):
        return 2


class CodecHvbContactorNegativeLeakVoltage(Codec):
    def decode(self, payload):
        raw_data = struct.unpack('>H', payload)[0]
        leak_voltage = float(raw_data) * 0.001
        states = [{'hvb_contactor_negative_leak_voltage': leak_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"Negative Contactor Leak Voltage: {leak_voltage:.01f} V ({raw_data:04X})"}

    def __len__(self):
        return 2


class CodecHvbContactorPositiveVoltage(Codec):
    def decode(self, payload):
        raw_data = struct.unpack('>H', payload)[0]
        voltage = float(raw_data) * 0.01
        states = [{'hvb_contactor_positive_voltage': voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"Positive Contactor Voltage: {voltage:.01f} V ({raw_data:04X})"}

    def __len__(self):
        return 2


class CodecHvbContactorNegativeVoltage(Codec):
    def decode(self, payload):
        raw_data = struct.unpack('>H', payload)[0]
        voltage = float(raw_data) * 0.01
        states = [{'hvb_contactor_negative_voltage': voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"Negative Contactor Voltage: {voltage:.02f} V ({raw_data:04X})"}

    def __len__(self):
        return 2


class CodecHvbContactorPositiveBusLeakResistance(Codec):
    def decode(self, payload):
        raw_data = struct.unpack('>H', payload)[0]
        leak_resistance = float(raw_data) * 25.0
        states = [{'hvb_contactor_positive_bus_leak_resistance': leak_resistance}]
        return {'payload': payload, 'states': states, 'decoded': f"Contactor Bus+ Leak Resistance: {leak_resistance:.0f} Ω ({raw_data:04X})"}

    def __len__(self):
        return 2


class CodecHvbContactorNegativeBusLeakResistance(Codec):
    def decode(self, payload):
        raw_data = struct.unpack('>H', payload)[0]
        leak_resistance = float(raw_data) * 25.0
        states = [{'hvb_contactor_negative_bus_leak_resistance': leak_resistance}]
        return {'payload': payload, 'states': states, 'decoded': f"Contactor Bus- Leak Resistance: {leak_resistance:.0f} Ω ({raw_data:04X})"}

    def __len__(self):
        return 2


class CodecHvbContactorOverallLeakResistance(Codec):
    def decode(self, payload):
        raw_data = struct.unpack('>H', payload)[0]
        leak_resistance = float(raw_data) * 25.0
        states = [{'hvb_contactor_overall_leak_resistance': leak_resistance}]
        return {'payload': payload, 'states': states, 'decoded': f"Contactor Overall Leak Resistance: {leak_resistance:.0f} Ω ({raw_data:04X})"}

    def __len__(self):
        return 2


class CodecHvbContactorOpenLeakResistance(Codec):
    def decode(self, payload):
        raw_data = struct.unpack('>H', payload)[0]
        leak_resistance = float(raw_data) * 25.0
        states = [{'hvb_contactor_open_leak_resistance': leak_resistance}]
        return {'payload': payload, 'states': states, 'decoded': f"Contactor Open Leak Resistance: {leak_resistance:.0f} Ω ({raw_data:04X})"}

    def __len__(self):
        return 2


class CodecManager:

    _codec_lookup = {
        DidId.Null:                             CodecNull,
        DidId.KeyState:                         CodecKeyState,
        DidId.InferredKey:                      CodecInferredKey,
        DidId.GearDisplayed:                    CodecGearDisplayed,
        DidId.GearCommanded:                    CodecGearCommanded,
        DidId.ChargePlug:                       CodecChargePlug,
        DidId.LoresOdometer:                    CodecLoresOdometer,
        DidId.HiresOdometer:                    CodecHiresOdometer,
        DidId.HiresSpeed:                       CodecHiresSpeed,
        DidId.EngineStart:                      CodecEngineStart,
        DidId.ExteriorTemp:                     CodecExteriorTemp,
        DidId.InteriorTemp:                     CodecInteriorTemp,
        DidId.Time:                             CodecTime,
        DidId.Gps:                              CodecGPS,
        DidId.HvbSoc:                           CodecHvbSoc,
        DidId.HvbSocD:                          CodecHvbSocD,
        DidId.HvbEtE:                           CodecHvbEtE,
        DidId.HvbSoH:                           CodecHvbSoH,
        DidId.HvbTemp:                          CodecHvbTemp,
        DidId.HvbVoltage:                       CodecHvbVoltage,
        DidId.HvbCurrent:                       CodecHvbCurrent,
        DidId.HvbCHP:                           CodecHvbCHP,
        DidId.HvbCHOp:                          CodecHvbCHOp,
        DidId.HvbContactorStatus:                       CodecHvbContactorStatus,
        DidId.HvbContactorPositiveLeakVoltage:          CodecHvbContactorPositiveLeakVoltage,
        DidId.HvbContactorNegativeLeakVoltage:          CodecHvbContactorNegativeLeakVoltage,
        DidId.HvbContactorPositiveVoltage:              CodecHvbContactorPositiveVoltage,
        DidId.HvbContactorNegativeVoltage:              CodecHvbContactorNegativeVoltage,
        DidId.HvbContactorPositiveBusLeakResistance:    CodecHvbContactorPositiveBusLeakResistance,
        DidId.HvbContactorNegativeBusLeakResistance:    CodecHvbContactorNegativeBusLeakResistance,
        DidId.HvbContactorOverallLeakResistance:        CodecHvbContactorOverallLeakResistance,
        DidId.HvbContactorOpenLeakResistance:           CodecHvbContactorOpenLeakResistance,
        DidId.ChargingStatus:                   CodecChargingStatus,
        DidId.EvseType:                         CodecEvseType,
        DidId.EvseDigitalMode:                  CodecEvseDigitalMode,
        DidId.ChargerStatus:                    CodecChargerStatus,
        DidId.ChargerInputVoltage:              CodecChargerInputVoltage,
        DidId.ChargerInputCurrent:              CodecChargerInputCurrent,
        DidId.ChargerInputFrequency:            CodecChargerInputFrequency,
        DidId.ChargerPilotVoltage:              CodecChargerPilotVoltage,
        DidId.ChargerPilotDutyCycle:            CodecChargerPilotDutyCycle,
        DidId.ChargerInputPowerAvailable:       CodecChargerInputPowerAvailable,
        DidId.ChargerMaxPower:                  CodecChargerMaxPower,
        DidId.ChargerOutputVoltage:             CodecChargerOutputVoltage,
        DidId.ChargerOutputCurrent:             CodecChargerOutputCurrent,
        DidId.ChargePowerLimit:                 CodecChargerPowerLimit,
        DidId.HvbChargeCurrentRequested:        CodecHvbChargeCurrentRequested,
        DidId.HvbChargeVoltageRequested:        CodecHvbChargeVoltageRequested,
        DidId.HvbMaximumChargeCurrent:          CodecHvbMaxChargeCurrent,
        DidId.LvbSoc:                           CodecLvbSoc,
        DidId.LvbVoltage:                       CodecLvbVoltage,
        DidId.LvbCurrent:                       CodecLvbCurrent,
        DidId.LvbDcDcEnable:                    CodecLvbDcDcEnable,
        DidId.LvbDcDcHVCurrent:                 CodecLvbDcDcHVCurrent,
        DidId.LvbDcDcLVCurrent:                 CodecLvbDcDcLVCurrent,
        DidId.EngineRunTime:                    CodecEngineRunTime,
    }

    _gps_server_enabled = False
    _gps_server = None
    _gps_server_timeout = 0.5

    def __init__(self, config: Configuration) -> None:
        self._codec_lookup = CodecManager._codec_lookup
        CodecManager._gps_server = dict(config).get('gps_server', None)
        CodecManager._gps_server_timeout = dict(config).get('gps_server_timeout', 0.5)
        if CodecManager._gps_server:
            CodecManager._gps_server_enabled = connect_gps_server()


    def codec(self, did_id: int) -> Codec:
        try:
            return self._codec_lookup.get(DidId(did_id), CodecNull)
        except ValueError:
            return CodecNull


def connect_gps_server() -> bool:
    CodecManager._gps_server_enabled = False
    for _ in range(1):
        try:
            _ = requests.get(CodecManager._gps_server, timeout=CodecManager._gps_server_timeout)
            CodecManager._gps_server_enabled = True
            break
        except (ReadTimeout, HTTPError, InvalidURL, InvalidSchema, ConnectTimeout, ConnectionError, MissingSchema) as e:
            continue
        except Exception as e:
            _LOGGER.exception(f"Unexpected exception testing for GPS server '{CodecManager._gps_server}': {e}")

    if CodecManager._gps_server_enabled:
        _LOGGER.info(f"Connected to precision GPS server '{CodecManager._gps_server}'")
    else:
        _LOGGER.error(f"Unable to connect to precision GPS server '{CodecManager._gps_server}', server is disabled")
    return CodecManager._gps_server_enabled
