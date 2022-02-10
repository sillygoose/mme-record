import logging
import struct

import requests
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout, HTTPError, InvalidURL, InvalidSchema

from udsoncan import DidCodec

from did import DidId
from config.configuration import Configuration


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
    def decode(self, payload):
        # default to using MME GPS data
        gps_elevation, gps_latitude, gps_longitude, _, gps_speed, gps_bearing = struct.unpack('>HllBHH', payload)
        gps_latitude /= 60.0
        gps_longitude /= 60.0
        gps_speed *= 3.6
        states = [
                {'gps_elevation': gps_elevation},
                {'gps_latitude': gps_latitude},
                {'gps_longitude': gps_longitude},
                {'gps_speed': gps_speed},
                {'gps_bearing': gps_bearing},
            ]

        # Use GPS server if available alternate
        if CodecManager._gps_server:
            try:
                gps_response = requests.get(CodecManager._gps_server, timeout=0.2)
                phone_gps = gps_response.json()
                gps_latitude = phone_gps.get('latitude')
                gps_longitude = phone_gps.get('longitude')
                gps_elevation = phone_gps.get('altitude')
                states = [
                        {'gps_elevation': gps_elevation},
                        {'gps_latitude': gps_latitude},
                        {'gps_longitude': gps_longitude},
                    ]
                if (gps_speed := phone_gps.get('speed')) >= 0.0:
                    states.append({'gps_speed': gps_speed * 3.6})
                if (gps_bearing := phone_gps.get('course')) >= 0.0:
                    states.append({'gps_bearing': gps_bearing})
            except InvalidSchema as e:
                _LOGGER.error(f"InvalidSchema error: {e}")
            except InvalidURL as e:
                _LOGGER.error(f"InvalidURL error: {e}")
            except HTTPError as e:
                _LOGGER.error(f"HTTP error: {e}")
            except ReadTimeout as e:
                _LOGGER.error(f"Read Time out: {e}")
            except ConnectTimeout as e:
                _LOGGER.error(f"Time out connecting to GPS server: {e}")
            except ConnectionError as e:
                _LOGGER.error(f"Unable to connect to GPS server: {e}")
            except Exception as e:
                _LOGGER.exception(f"Unexpected exception: {e}")

        gps_data = f"GPS: ({gps_latitude:2.8f}, {gps_longitude:2.8f}), elevation {gps_elevation:.01f} m, bearing {gps_bearing}°, speed {gps_speed:3.1f} kph"
        return {'payload': payload, 'states': states, 'decoded': gps_data}

    def __len__(self):
        return 15


class CodecLoresOdometer(Codec):
    def decode(self, payload):
        odometer_high, odometer_low = struct.unpack('>HB', payload)
        lores_odometer = odometer_high * 256 + odometer_low
        states = [{'lores_odometer': lores_odometer}]
        return {'payload': payload, 'states': states, 'decoded': f"Lores odometer: {lores_odometer} km"}

    def __len__(self):
        return 3


class CodecHiresOdometer(Codec):
    def decode(self, payload):
        odometer_high, odometer_low = struct.unpack('>HB', payload)
        hires_odometer = (odometer_high * 256 + odometer_low) * 0.1
        states = [{'hires_odometer': hires_odometer}]
        return {'payload': payload, 'states': states, 'decoded': f"Hires odometer: {hires_odometer:.1f} km"}

    def __len__(self):
        return 3


class CodecHiresSpeed(Codec):
    def decode(self, payload):
        hires_speed = struct.unpack('>H', payload)[0]
        hires_speed = hires_speed / 128.0
        states = [{'hires_speed': hires_speed}]
        return {'payload': payload, 'states': states, 'decoded': f"Speed: {hires_speed:.0f} kph"}

    def __len__(self):
        return 2


class CodecExteriorTemp(Codec):
    def decode(self, payload):
        exterior_temp = struct.unpack('>B', payload)[0] - 40
        states = [{'exterior_temp': exterior_temp}]
        return {'payload': payload, 'states': states, 'decoded': f"Exterior temperature is {exterior_temp}°C"}

    def __len__(self):
        return 1


class CodecInteriorTemp(Codec):
    def decode(self, payload):
        interior_temp = struct.unpack('>B', payload)[0] - 40
        states = [{'interior_temp': interior_temp}]
        return {'payload': payload, 'states': states, 'decoded': f"Interior temperature is {interior_temp}°C"}

    def __len__(self):
        return 1


class CodecTime(Codec):
    def decode(self, payload):
        car_time = struct.unpack('>L', payload)[0] * 0.1
        states = [{'time': car_time}]
        return {'payload': payload, 'states': states, 'decoded': f"MME time is {car_time:.1f} s"}

    def __len__(self):
        return 4


class CodecHvbSoc(Codec):
    def decode(self, payload):
        hvb_soc = struct.unpack('>H', payload)[0] * 0.002
        states = [{'hvb_soc': hvb_soc}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB internal SoC is {hvb_soc:.3f}%"}

    def __len__(self):
        return 2


class CodecHvbSocD(Codec):
    def decode(self, payload):
        hvb_socd = struct.unpack('>B', payload)[0] * 0.5
        states = [{'hvb_socd': hvb_socd}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB displayed SoC is {hvb_socd:.0f}% ({hvb_socd:.1f}%)"}

    def __len__(self):
        return 1


class CodecHvbEtE(Codec):
    def decode(self, payload):
        hvb_ete = struct.unpack('>H', payload)[0] * 2
        states = [{'hvb_ete': hvb_ete}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB energy to empty is {hvb_ete:.0f} Wh"}

    def __len__(self):
        return 2


class CodecHvbTemp(Codec):
    def decode(self, payload):
        hvb_temp = struct.unpack('>B', payload)[0] - 50
        states = [{'hvb_temp': hvb_temp}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB temp is {hvb_temp}°C"}

    def __len__(self):
        return 1


class CodecHvbCHP(Codec):
    # INT16(A:B)×.001
    def decode(self, payload):
        hvb_chp = struct.unpack('>H', payload)[0] * 0.001
        states = [{'hvb_chp': hvb_chp}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB coolant heater power is {hvb_chp} W"}

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
        lvb_soc = struct.unpack('>B', payload)[0]
        states = [{'lvb_soc': lvb_soc}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB SoC is {lvb_soc}%"}

    def __len__(self):
        return 1


class CodecLvbVoltage(Codec):
    def decode(self, payload):
        lvb_voltage = struct.unpack('>B', payload)[0] * 0.05 + 6.0
        states = [{'lvb_voltage': lvb_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB voltage is {lvb_voltage:.01f} V"}

    def __len__(self):
        return 1

class CodecLvbCurrent(Codec):
    def decode(self, payload):
        lvb_current = struct.unpack('>B', payload)[0] - 127
        states = [{'lvb_current': lvb_current}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB current is {lvb_current} A"}

    def __len__(self):
        return 1


class CodecHvbVoltage(Codec):
    def decode(self, payload):
        hvb_voltage = struct.unpack('>H', payload)[0] * 0.01
        states = [{'hvb_voltage': hvb_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB voltage is {hvb_voltage:.2f} V"}

    def __len__(self):
        return 2


class CodecHvbCurrent(Codec):
    def decode(self, payload):
        current_msb, current_lsb = struct.unpack('>bB', payload)
        hvb_current = (current_msb * 256 + current_lsb) * 0.1
        states = [{'hvb_current': hvb_current}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB current is {hvb_current:.1f} A"}

    def __len__(self):
        return 2


class CodecChargingStatus(Codec):
    def decode(self, payload):
        charging_status = struct.unpack('>B', payload)[0]
        charging_statuses = {
            0: 'Not Ready', 1: 'Wait', 2: 'Ready', 3: 'Charging', 4: 'Done', 5: 'Fault',
        }
        status_string = 'Charger status: ' + charging_statuses.get(charging_status, f"unknown ({charging_status})")
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


class CodecHvbSOH(Codec):
    def decode(self, payload):
        hvb_soh = struct.unpack('>B', payload)[0] * 0.5
        states = [{'hvb_soh': hvb_soh}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB SOH is {hvb_soh:.2f} %"}

    def __len__(self):
        return 1


class CodecChargerInputVoltage(Codec):
    def decode(self, payload):
        charger_input_voltage = struct.unpack('>H', payload)[0] * 0.01
        states = [{'charger_input_voltage': charger_input_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger input voltage is {charger_input_voltage:.1f} V"}

    def __len__(self):
        return 2


class CodecChargerInputCurrent(Codec):
    def decode(self, payload):
        charger_input_current = struct.unpack('>B', payload)[0]
        states = [{'charger_input_current': charger_input_current}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger input current is {charger_input_current} A"}

    def __len__(self):
        return 1


class CodecChargerInputFrequency(Codec):
    def decode(self, payload):
        charger_input_frequency = struct.unpack('>B', payload)[0] * 0.5
        states = [{'charger_input_frequency': charger_input_frequency}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger input frequency is {charger_input_frequency:.1f} Hz"}

    def __len__(self):
        return 1


class CodecChargerPilotVoltage(Codec):
    def decode(self, payload):
        charger_pilot_voltage = struct.unpack('>B', payload)[0] * 0.1
        states = [{'charger_pilot_voltage': charger_pilot_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger pilot voltage is {charger_pilot_voltage:.1f} V"}

    def __len__(self):
        return 1


class CodecChargerPilotDutyCycle(Codec):
    def decode(self, payload):
        charger_pilot_duty_cycle = struct.unpack('>B', payload)[0] * 0.5
        states = [{'charger_pilot_duty_cycle': charger_pilot_duty_cycle}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger pilot duty cycle is {charger_pilot_duty_cycle:.1f}"}

    def __len__(self):
        return 1


class CodecChargerInputPowerAvailable(Codec):
    def decode(self, payload):
        charger_input_power_available = struct.unpack('>h', payload)[0] * 0.005
        states = [{'charger_input_power_available': charger_input_power_available}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger input power available is {charger_input_power_available:.1f} kW"}

    def __len__(self):
        return 2


class CodecChargerMaxPower(Codec):
    def decode(self, payload):
        charger_max_power = struct.unpack('>H', payload)[0] * 0.05
        states = [{'charger_max_power': charger_max_power}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger maximum power is {charger_max_power:.3f} kW"}

    def __len__(self):
        return 2


class CodecChargerOutputVoltage(Codec):
    def decode(self, payload):
        charger_output_voltage = struct.unpack('>H', payload)[0] * 0.01
        states = [{'charger_output_voltage': charger_output_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger output voltage is {charger_output_voltage:.1f} V"}

    def __len__(self):
        return 2


class CodecChargerOutputCurrent(Codec):
    def decode(self, payload):
        charger_output_current = struct.unpack('>h', payload)[0] * 0.01
        states = [{'charger_output_current': charger_output_current}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger output current is {charger_output_current:.1f} A"}

    def __len__(self):
        return 2


class CodecChargerPowerLimit(Codec):
    def decode(self, payload):
        charger_power_limit = struct.unpack('>h', payload)[0] * 0.1
        states = [{'charger_power_limit': charger_power_limit}]
        return {'payload': payload, 'states': states, 'decoded': f"Charge power limit is {charger_power_limit:.1f} A"}

    def __len__(self):
        return 2


class CodecHvbChargeCurrentRequested(Codec):
    def decode(self, payload):
        hvb_charge_current_requested = struct.unpack('>h', payload)[0] * 0.01
        states = [{'hvb_charge_current_requested': hvb_charge_current_requested}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB charge current requested is {hvb_charge_current_requested:.1f} A"}

    def __len__(self):
        return 2


class CodecHvbChargeVoltageRequested(Codec):
    def decode(self, payload):
        hvb_charge_voltage_requested = struct.unpack('>B', payload)[0] * 2
        states = [{'hvb_charge_voltage_requested': hvb_charge_voltage_requested}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB charge voltage requested is {hvb_charge_voltage_requested} V"}

    def __len__(self):
        return 1


class CodecHvbMaxChargeCurrent(Codec):
    def decode(self, payload):
        hvb_max_charge_current = struct.unpack('>h', payload)[0] * 0.05
        states = [{'hvb_max_charge_current': hvb_max_charge_current}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB maximum charge current is {hvb_max_charge_current:.1f} A"}

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
        return {'payload': payload, 'states': states, 'decoded': f"LVB DC-DC HV current is {lvb_dcdc_hv_current:.1f} A"}

    def __len__(self):
        return 1


class CodecLvbDcDcLVCurrent(Codec):
    def decode(self, payload):
        lvb_dcdc_lv_current = struct.unpack('>B', payload)[0]
        states = [{'lvb_dcdc_lv_current': lvb_dcdc_lv_current}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB DC-DC LV current is {lvb_dcdc_lv_current} A"}

    def __len__(self):
        return 1


class CodecManager:

    _codec_lookup = {
        DidId.Null:                           CodecNull,
        DidId.KeyState:                       CodecKeyState,
        DidId.InferredKey:                    CodecInferredKey,
        DidId.GearDisplayed:                  CodecGearDisplayed,
        DidId.GearCommanded:                  CodecGearCommanded,
        DidId.ChargePlug:                     CodecChargePlug,
        DidId.LoresOdometer:                  CodecLoresOdometer,
        DidId.HiresOdometer:                  CodecHiresOdometer,
        DidId.HiresSpeed:                     CodecHiresSpeed,
        DidId.EngineStart:                    CodecEngineStart,
        DidId.ExteriorTemp:                   CodecExteriorTemp,
        DidId.InteriorTemp:                   CodecInteriorTemp,
        DidId.Time:                           CodecTime,
        DidId.Gps:                            CodecGPS,
        DidId.HvbSoc:                         CodecHvbSoc,
        DidId.HvbSocD:                        CodecHvbSocD,
        DidId.HvbEtE:                         CodecHvbEtE,
        DidId.HvbSOH:                         CodecHvbSOH,
        DidId.HvbTemp:                        CodecHvbTemp,
        DidId.HvbVoltage:                     CodecHvbVoltage,
        DidId.HvbCurrent:                     CodecHvbCurrent,
        DidId.HvbCHP:                         CodecHvbCHP,
        DidId.HvbCHOp:                        CodecHvbCHOp,
        DidId.ChargingStatus:                 CodecChargingStatus,
        DidId.EvseType:                       CodecEvseType,
        DidId.EvseDigitalMode:                CodecEvseDigitalMode,
        DidId.ChargerStatus:                  CodecChargerStatus,
        DidId.ChargerInputVoltage:            CodecChargerInputVoltage,
        DidId.ChargerInputCurrent:            CodecChargerInputCurrent,
        DidId.ChargerInputFrequency:          CodecChargerInputFrequency,
        DidId.ChargerPilotVoltage:            CodecChargerPilotVoltage,
        DidId.ChargerPilotDutyCycle:          CodecChargerPilotDutyCycle,
        DidId.ChargerInputPowerAvailable:     CodecChargerInputPowerAvailable,
        DidId.ChargerMaxPower:                CodecChargerMaxPower,
        DidId.ChargerOutputVoltage:           CodecChargerOutputVoltage,
        DidId.ChargerOutputCurrent:           CodecChargerOutputCurrent,
        DidId.ChargePowerLimit:               CodecChargerPowerLimit,
        DidId.HvbChargeCurrentRequested:      CodecHvbChargeCurrentRequested,
        DidId.HvbChargeVoltageRequested:      CodecHvbChargeVoltageRequested,
        DidId.HvbMaximumChargeCurrent:        CodecHvbMaxChargeCurrent,
        DidId.LvbSoc:                         CodecLvbSoc,
        DidId.LvbVoltage:                     CodecLvbVoltage,
        DidId.LvbCurrent:                     CodecLvbCurrent,
        DidId.LvbDcDcEnable:                  CodecLvbDcDcEnable,
        DidId.LvbDcDcHVCurrent:               CodecLvbDcDcHVCurrent,
        DidId.LvbDcDcLVCurrent:               CodecLvbDcDcLVCurrent,
        DidId.EngineRunTime:                  CodecEngineRunTime,
    }

    def __init__(self, config: Configuration) -> None:
        self._codec_lookup = CodecManager._codec_lookup
        record_config = dict(config.record)
        CodecManager._gps_server = record_config.get('gps_server', None)

    def codec(self, did_id: int) -> Codec:
        try:
            return self._codec_lookup.get(DidId(did_id), CodecNull)
        except ValueError:
            return CodecNull