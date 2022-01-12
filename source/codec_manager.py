import struct

from udsoncan import DidCodec

from did import DidId


class Codec(DidCodec):
    def encode(self, val):
        return val


class CodecNull(Codec):
    def decode(self, payload):
        return {'payload': payload, 'states': {}, 'decoded': list(payload)}

    def __len__(self):
        raise Codec.ReadAllRemainingData


class CodecKeyState(Codec):
    def decode(self, payload):
        key_state = struct.unpack('>B', payload)[0]
        key_states = {0: 'Sleeping', 3: 'On', 4: 'Starting', 5: 'Off'}
        state_string = 'Ignition state: ' + key_states.get(key_state, 'Unknown')
        states = [{'key_state': key_state}]
        return {'payload': payload, 'states': states, 'decoded': state_string}

    def __len__(self):
        return 1


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
        elevation, latitude, longitude, fix, speed, bearing = struct.unpack('>HllBHH', payload)
        latitude /= 60.0
        longitude /= 60.0
        speed *= 3.6
        gps_data = f"GPS: ({latitude:2.5f}, {longitude:2.5f}), elevation {elevation} m, bearing {bearing}°, speed {speed:3.1f} kph, fix is {fix}"
        states = [
                {'elevation': elevation},
                {'latitude': latitude},
                {'longitude': longitude},
                {'fix': fix},
                {'speed': speed},
                {'bearing': bearing},
            ]
        return {'payload': payload, 'states': states, 'decoded': gps_data}

    def __len__(self):
        return 15


class CodecHiresOdometer(Codec):
    def decode(self, payload):
        odometer_high, odometer_low = struct.unpack('>HB', payload)
        odometer = (odometer_high * 256 + odometer_low) * 0.1
        states = [{'hires_odometer': odometer}]
        return {'payload': payload, 'states': states, 'decoded': f"Hires odometer: {odometer:.1f} km"}

    def __len__(self):
        return 3


class CodecHiresSpeed(Codec):
    def decode(self, payload):
        hires_speed = struct.unpack('>H', payload)[0]
        speed = hires_speed / 128.0
        states = [{'speed': speed}]
        return {'payload': payload, 'states': states, 'decoded': f"Speed: {speed:.0f} kph"}

    def __len__(self):
        return 2


class CodecExteriorTemp(Codec):
    def decode(self, payload):
        temp = struct.unpack('>B', payload)[0] - 40
        states = [{'ext_temp': temp}]
        return {'payload': payload, 'states': states, 'decoded': f"Exterior temperature is {temp}°C"}

    def __len__(self):
        return 1


class CodecInteriorTemp(Codec):
    def decode(self, payload):
        temp = struct.unpack('>B', payload)[0] - 40
        states = [{'int_temp': temp}]
        return {'payload': payload, 'states': states, 'decoded': f"Interior temperature is {temp}°C"}

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
        soc = struct.unpack('>H', payload)[0] * 0.002
        states = [{'soc': soc}]
        return {'payload': payload, 'states': states, 'decoded': f"Internal SOC is {soc:.3f}%"}

    def __len__(self):
        return 2


class CodecHvbSocD(Codec):
    def decode(self, payload):
        soc_displayed = struct.unpack('>B', payload)[0] * 0.5
        states = [{'soc_displayed': soc_displayed}]
        return {'payload': payload, 'states': states, 'decoded': f"Displayed SOC is {soc_displayed:.0f}%"}

    def __len__(self):
        return 1


class CodecHvbEte(Codec):
    def decode(self, payload):
        energyToEmpty = struct.unpack('>H', payload)[0] * 0.002
        states = [{'HVBete': energyToEmpty}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB energy to empty is {energyToEmpty:.3f} kWh"}

    def __len__(self):
        return 2


class CodecHvbTemp(Codec):
    def decode(self, payload):
        temp = struct.unpack('>B', payload)[0] - 50
        states = [{'hvb_temp': temp}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB temp is {temp}°C"}

    def __len__(self):
        return 1


class CodecLvbSoc(Codec):
    def decode(self, payload):
        soc = struct.unpack('>B', payload)[0]
        states = [{'lvb_soc': soc}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB SOC is {soc}%"}

    def __len__(self):
        return 1


class CodecLvbVoltage(Codec):
    def decode(self, payload):
        voltage = struct.unpack('>B', payload)[0] * 0.05 + 6.0
        states = [{'lvb_voltage': voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB voltage is {voltage:.2f} V"}

    def __len__(self):
        return 1

class CodecLvbCurrent(Codec):
    def decode(self, payload):
        current = struct.unpack('>B', payload)[0] - 127
        states = [{'lvb_current': current}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB current is {current} A"}

    def __len__(self):
        return 1


class CodecHvbVoltage(Codec):
    def decode(self, payload):
        voltage = struct.unpack('>H', payload)[0] * 0.01
        states = [{'hvb_voltage': voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB voltage is {voltage:.2f} V"}

    def __len__(self):
        return 2


class CodecHvbCurrent(Codec):
    def decode(self, payload):
        current_msb, current_lsb = struct.unpack('>bB', payload)
        current = (current_msb * 256 + current_lsb) * 0.1
        states = [{'hvb_current': current}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB current is {current:.1f} A"}

    def __len__(self):
        return 2


class CodecChargingStatus(Codec):
    def decode(self, payload):
        charging_status = struct.unpack('>B', payload)[0]
        charging_statuses = {
            0: 'Not Ready', 1: 'Wait', 2: 'Ready', 3: 'Charging', 4: 'Done', 5: 'Fault',
        }
        status_string = 'Charger status: ' + charging_statuses.get(charging_status, f"unknown ({charging_status:02X})")
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
        status_string = 'Charger status: ' + charger_statuses.get(charger_status, f"unknown ({charger_status:02X})")
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
        type_string = 'EVSE type: ' + evse_types.get(type, 'unknown')
        states = [{'evse_type': evse_type}]
        return {'payload': payload, 'states': states, 'decoded': type_string}

    def __len__(self):
        return 1


class CodecEvseDigitalMode(Codec):
    def decode(self, payload):
        digital_mode = struct.unpack('>B', payload)[0]
        digital_modes = { 0: 'None', 1: 'DCE-', 2: 'DC-P', 3: 'DCEP', 4: 'ACE-', 5: 'AC-P', 6: 'ACEP', 7: 'Rst', 8: 'Off', 9: 'Est', 10: 'FAIL' }
        mode = digital_modes.get(digital_mode, "???")
        states = [{'evse_digital_mode': digital_mode}]
        return {'payload': payload, 'states': states, 'decoded': ('EVSE digital mode: ' + mode)}

    def __len__(self):
        return 1


class CodecHvbSOH(Codec):
    def decode(self, payload):
        soh = struct.unpack('>B', payload)[0] * 0.5
        states = [{'soh': soh}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB SOH is {soh:.2f} %"}

    def __len__(self):
        return 1


class CodecChargerInputVoltage(Codec):
    def decode(self, payload):
        ac_voltage = struct.unpack('>H', payload)[0] * 0.01
        states = [{'ac_voltage': ac_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger input voltage is {ac_voltage:.1f} V"}

    def __len__(self):
        return 2


class CodecChargerInputCurrent(Codec):
    def decode(self, payload):
        ac_current = struct.unpack('>B', payload)[0]
        states = [{'ac_current': ac_current}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger input current is {ac_current} A"}

    def __len__(self):
        return 1


class CodecChargerInputFrequency(Codec):
    def decode(self, payload):
        ac_frequency = struct.unpack('>B', payload)[0] * 0.5
        states = [{'ac_frequency': ac_frequency}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger input frequency is {ac_frequency:.1f} Hz"}

    def __len__(self):
        return 1


class CodecChargerPilotVoltage(Codec):
    def decode(self, payload):
        pilot_voltage = struct.unpack('>B', payload)[0] * 0.1
        states = [{'pilot_voltage': pilot_voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger pilot voltage is {pilot_voltage:.1f} V"}

    def __len__(self):
        return 1


class CodecChargerPilotDutyCycle(Codec):
    def decode(self, payload):
        duty_cycle = struct.unpack('>B', payload)[0] * 0.5
        states = [{'duty_cycle': duty_cycle}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger pilot duty cycle is {duty_cycle:.1f}"}

    def __len__(self):
        return 1


class CodecChargerInputPower(Codec):
    def decode(self, payload):
        charger_power = struct.unpack('>h', payload)[0] * 0.005
        states = [{'charger_power': charger_power}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger input power available is {charger_power:.1f} kW"}

    def __len__(self):
        return 2


class CodecChargerMaxPower(Codec):
    def decode(self, payload):
        max_power = struct.unpack('>H', payload)[0] * 0.05
        states = [{'max_power': max_power}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger maximum power is {max_power:.3f} kW"}

    def __len__(self):
        return 2


class CodecChargerOutputVoltage(Codec):
    def decode(self, payload):
        v_out = struct.unpack('>h', payload)[0] * 0.01
        states = [{'v_out': v_out}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger output voltage is {v_out:.1f} V"}

    def __len__(self):
        return 2


class CodecChargerOutputCurrent(Codec):
    def decode(self, payload):
        a_out = struct.unpack('>h', payload)[0] * 0.01
        states = [{'a_out': a_out}]
        return {'payload': payload, 'states': states, 'decoded': f"AC charger output current is {a_out:.1f} A"}

    def __len__(self):
        return 2


class CodecChargePowerLimit(Codec):
    def decode(self, payload):
        power_limit = struct.unpack('>h', payload)[0] * 0.1
        states = [{'power_limit': power_limit}]
        return {'payload': payload, 'states': states, 'decoded': f"Charge power limit is {power_limit:.1f} A"}

    def __len__(self):
        return 2


class CodecHvbChargeCurrentRequested(Codec):
    def decode(self, payload):
        current_requested = struct.unpack('>h', payload)[0] * 0.01
        states = [{'current_requested': current_requested}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB charge current requested is {current_requested:.1f} A"}

    def __len__(self):
        return 2


class CodecHvbChargeVoltageRequested(Codec):
    def decode(self, payload):
        voltage_requested = struct.unpack('>B', payload)[0] * 2
        states = [{'voltage_requested': voltage_requested}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB charge voltage requested is {voltage_requested} V"}

    def __len__(self):
        return 1


class CodecHvbMaximumChargeCurrent(Codec):
    def decode(self, payload):
        max_current = struct.unpack('>h', payload)[0] * 0.05
        states = [{'max_current': max_current}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB maximum charge current is {max_current:.1f} A"}

    def __len__(self):
        return 2


class CodecLvbDcDcEnable(Codec):
    def decode(self, payload):
        enable = struct.unpack('>H', payload)[0] & 0x0001
        states = [{'dcdc_enable': enable}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB DC-DC enable is {enable}"}

    def __len__(self):
        return 2


class CodecLvbDcDcHVCurrent(Codec):
    def decode(self, payload):
        current = struct.unpack('>B', payload)[0] * 0.1
        states = [{'hv_current': current}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB DC-DC HV current is {current:.1f} A"}

    def __len__(self):
        return 1


class CodecLvbDcDcLVCurrent(Codec):
    def decode(self, payload):
        current = struct.unpack('>B', payload)[0]
        states = [{'lv_current': current}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB DC-DC LV current is {current} A"}

    def __len__(self):
        return 1


class CodecManager:

    _codec_lookup = {
        DidId.Null:                           CodecNull,
        DidId.KeyState:                       CodecKeyState,
        DidId.GearDisplayed:                  CodecGearDisplayed,
        DidId.GearCommanded:                  CodecGearCommanded,
        DidId.HiresOdometer:                  CodecHiresOdometer,
        DidId.HiresSpeed:                     CodecHiresSpeed,
        DidId.ExteriorTemp:                   CodecExteriorTemp,
        DidId.InteriorTemp:                   CodecInteriorTemp,
        DidId.Time:                           CodecTime,
        DidId.Gps:                            CodecGPS,
        DidId.HvbSoc:                         CodecHvbSoc,
        DidId.HvbSocD:                        CodecHvbSocD,
        DidId.HvbEte:                         CodecHvbEte,
        DidId.HvbSOH:                         CodecHvbSOH,
        DidId.HvbTemp:                        CodecHvbTemp,
        DidId.HvbVoltage:                     CodecHvbVoltage,
        DidId.HvbCurrent:                     CodecHvbCurrent,
        DidId.ChargingStatus:                 CodecChargingStatus,
        DidId.EvseType:                       CodecEvseType,
        DidId.EvseDigitalMode:                CodecEvseDigitalMode,
        DidId.HvbSOH:                         CodecHvbSOH,
        DidId.ChargerStatus:                  CodecChargerStatus,
        DidId.ChargerInputVoltage:            CodecChargerInputVoltage,
        DidId.ChargerInputCurrent:            CodecChargerInputCurrent,
        DidId.ChargerInputFrequency:          CodecChargerInputFrequency,
        DidId.ChargerPilotVoltage:            CodecChargerPilotVoltage,
        DidId.ChargerPilotDutyCycle:          CodecChargerPilotDutyCycle,
        DidId.ChargerInputPower:              CodecChargerInputPower,
        DidId.ChargerMaxPower:                CodecChargerMaxPower,
        DidId.ChargerOutputVoltage:           CodecChargerOutputVoltage,
        DidId.ChargerOutputCurrent:           CodecChargerOutputCurrent,
        DidId.ChargePowerLimit:               CodecChargePowerLimit,
        DidId.HvbChargeCurrentRequested:      CodecHvbChargeCurrentRequested,
        DidId.HvbChargeVoltageRequested:      CodecHvbChargeVoltageRequested,
        DidId.HvbMaximumChargeCurrent:        CodecHvbMaximumChargeCurrent,
        DidId.LvbSoc:                         CodecLvbSoc,
        DidId.LvbVoltage:                     CodecLvbVoltage,
        DidId.LvbCurrent:                     CodecLvbCurrent,
        DidId.LvbDcDcEnable:                  CodecLvbDcDcEnable,
        DidId.LvbDcDcHVCurrent:               CodecLvbDcDcHVCurrent,
        DidId.LvbDcDcLVCurrent:               CodecLvbDcDcLVCurrent,
    }

    def __init__(self, config: dict) -> None:
        self._config = config
        self._codec_lookup = CodecManager._codec_lookup

    def codec(self, did_id: int) -> Codec:
        return self._codec_lookup.get(DidId(did_id), None)
