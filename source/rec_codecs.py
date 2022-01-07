import struct

from codec import Codec, CodecId


class CodecNull(Codec):
    def decode(self, payload):
        return {'payload': payload, 'states': {}, 'decoded': list(payload)}

    def __len__(self):
        raise Codec.ReadAllRemainingData


class CodecKeyState(Codec):
    def decode(self, payload):
        key_state = struct.unpack('>B', payload)
        if key_state[0] == 0x00:
            state_string = 'Ignition state: unknown or sleeping'
        elif key_state[0] == 0x05:
            state_string = 'Ignition state: Off'
        elif key_state[0] == 0x03:
            state_string = 'Ignition state: On'
        elif key_state[0] == 0x04:
            state_string = 'Ignition state: Starting'
        else:
            state_string = 'ERROR: Unsupported decode'
        states = [{'key_state': key_state}]
        return {'payload': payload, 'states': states, 'decoded': state_string}

    def __len__(self):
        return 1


class CodecGearDisplayed(Codec):
    def decode(self, payload):
        # LOOKUP(A) 0=‘P’, 1=‘R’, 2=’N’, 3=‘D’, 4='L'
        gears = ['Park', 'Reverse', 'Neutral', 'Drive', 'Low']
        gear = 'Gear selected: '
        gear_displayed = struct.unpack('>B', payload)
        if gear_displayed[0] >= len(gears):
            gear += 'Unknown'
        else:
            gear += gears[gear_displayed[0]]
        states = [{'gear_displayed': gear_displayed}]
        return {'payload': payload, 'states': states, 'decoded': gear}

    def __len__(self):
        return 1


class CodecGearCommanded(Codec):
    def decode(self, payload):
        # LOOKUP(A) 70=‘P’, 60=‘R’, 50=’N’, 40=‘D’, 20='L'
        gears = {70: 'Park', 60: 'Reverse', 50: 'Neutral', 40: 'Drive', 20: 'Low', 255: 'Fault'}
        gear_commanded = struct.unpack('>B', payload)
        gear_commanded = gear_commanded[0]
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


class CodecOdometer(Codec):
    def decode(self, payload):
        odometer_high, odometer_low = struct.unpack('>HB', payload)
        odometer = (odometer_high * 256 + odometer_low) * 0.1
        states = [{'odometer': odometer}]
        return {'payload': payload, 'states': states, 'decoded': f"Odometer: {odometer:.1f} km"}

    def __len__(self):
        return 3


class CodecHiresSpeed(Codec):
    def decode(self, payload):
        hires_speed = struct.unpack('>H', payload)
        speed = hires_speed[0] / 128.0
        states = [{'speed': speed}]
        return {'payload': payload, 'states': states, 'decoded': f"Speed: {speed:.0f} kph"}

    def __len__(self):
        return 2


class CodecExteriorTemp(Codec):
    def decode(self, payload):
        temp = struct.unpack('>B', payload)
        temp = temp[0] - 40
        states = [{'ext_temp': temp}]
        return {'payload': payload, 'states': states, 'decoded': f"Exterior temperature is {temp}°C"}

    def __len__(self):
        return 1


class CodecInteriorTemp(Codec):
    def decode(self, payload):
        temp = struct.unpack('>B', payload)
        temp = temp[0] - 40
        states = [{'int_temp': temp}]
        return {'payload': payload, 'states': states, 'decoded': f"Interior temperature is {temp}°C"}

    def __len__(self):
        return 1


class CodecTime(Codec):
    def decode(self, payload):
        car_time = struct.unpack('>L', payload)
        car_time = car_time[0] * 0.1
        states = [{'time': car_time}]
        return {'payload': payload, 'states': states, 'decoded': f"MME time is {car_time:.1f} s"}

    def __len__(self):
        return 4


class CodecHvbSoc(Codec):
    def decode(self, payload):
        soc = struct.unpack('>H', payload)
        soc = soc[0] * 0.002
        states = [{'soc': soc}]
        return {'payload': payload, 'states': states, 'decoded': f"Internal SOC is {soc:.3f}%"}

    def __len__(self):
        return 2


class CodecHvbSocD(Codec):
    def decode(self, payload):
        soc_displayed = struct.unpack('>B', payload)
        soc_displayed = soc_displayed[0] * 0.5
        states = [{'soc_displayed': soc_displayed}]
        return {'payload': payload, 'states': states, 'decoded': f"Displayed SOC is {soc_displayed:.0f}%"}

    def __len__(self):
        return 1


class CodecHvbEte(Codec):
    def decode(self, payload):
        energyToEmpty = struct.unpack('>H', payload)
        energyToEmpty = energyToEmpty[0] * 0.002
        states = [{'HVBete': energyToEmpty}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB energy to empty is {energyToEmpty:.3f} kWh"}

    def __len__(self):
        return 2


class CodecHvbTemp(Codec):
    def decode(self, payload):
        temp = struct.unpack('>B', payload)
        temp = temp[0] - 50
        states = [{'hvb_temp': temp}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB temp is {temp}°C"}

    def __len__(self):
        return 1


class CodecLvbSoc(Codec):
    def decode(self, payload):
        soc = struct.unpack('>B', payload)
        soc = soc[0]
        states = [{'lvb_soc': soc}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB SOC is {soc}%"}

    def __len__(self):
        return 1


class CodecLvbVoltage(Codec):
    def decode(self, payload):
        # A*0.05+6
        voltage = struct.unpack('>B', payload)
        voltage = voltage[0] * 0.05 + 6.0
        states = [{'lvb_voltage': voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB voltage is {voltage:.2f} V"}

    def __len__(self):
        return 1

class CodecLvbCurrent(Codec):
    def decode(self, payload):
        # A*0.05+6
        current = struct.unpack('>B', payload)
        current = current[0] - 127
        states = [{'lvb_current': current}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB current is {current} A"}

    def __len__(self):
        return 1


class CodecHvbVoltage(Codec):
    def decode(self, payload):
        voltage = struct.unpack('>H', payload)
        voltage = voltage[0] * 0.01
        states = [{'hvb_voltage': voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB voltage is {voltage:.2f} V"}

    def __len__(self):
        return 2


class CodecHvbCurrent(Codec):
    # ((signed(A)*256)+B)*0.1
    def decode(self, payload):
        current_msb, current_lsb = struct.unpack('>bB', payload)
        current = (current_msb * 256 + current_lsb) * 0.1
        states = [{'hvb_current': current}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB current is {current:.1f} A"}

    def __len__(self):
        return 2


class CodecChargerStatus(Codec):
    def decode(self, payload):
        status = struct.unpack('>B', payload)
        status = status[0]
        charger_statuses = {
            0: 'Not Ready', 1: 'Ready', 2: 'Fault', 3: 'WChk', 4: 'PreC', 5: 'Charging',
            6: 'Done', 7: 'ExtC', 8: 'Init',
        }
        status_string = 'Charger status: ' + charger_statuses.get(status, 'unknown')
        states = [{'charger_status': status}]
        return {'payload': payload, 'states': states, 'decoded': status_string}

    def __len__(self):
        return 1


class CodecEvseType(Codec):
    def decode(self, payload):
        type = struct.unpack('>B', payload)
        type = type[0]
        evse_types = {
            0: 'None', 1: 'Level 1', 2: 'Level 2', 3: 'DC', 4: 'Bas', 5: 'HL',
            6: 'BasAC', 7: 'HLAC', 8: 'HLDC', 9: 'Unknown', 10: 'NCom',
            11: 'FAULT', 12: 'HEnd'
        }
        type_string = 'EVSE type: ' + evse_types.get(type, 'unknown')
        states = [{'evse_types': type}]
        return {'payload': payload, 'states': states, 'decoded': type_string}

    def __len__(self):
        return 1


class CodecEvseDigitalMode(Codec):
    def decode(self, payload):
        digital_mode = struct.unpack('>B', payload)
        digital_modes = { 0: 'None', 1: 'DCE-', 2: 'DC-P', 3: 'DCEP', 4: 'ACE-', 5: 'AC-P', 6: 'ACEP', 7: 'Rst', 8: 'Off', 9: 'Est', 10: 'FAIL' }
        mode = digital_modes.get(digital_mode[0], "???")
        states = [{'evse_digital_mode': digital_mode}]
        return {'payload': payload, 'states': states, 'decoded': ('EVSE digital mode: ' + mode)}

    def __len__(self):
        return 1


codecs = {
    CodecId.Null:                  CodecNull,
    CodecId.KeyState:              CodecKeyState,
    CodecId.GearDisplayed:         CodecGearDisplayed,
    CodecId.GearCommanded:         CodecGearCommanded,
    CodecId.Odometer:              CodecOdometer,
    CodecId.HiresSpeed:            CodecHiresSpeed,
    CodecId.ExteriorTemp:          CodecExteriorTemp,
    CodecId.InteriorTemp:          CodecInteriorTemp,
    CodecId.Time:                  CodecTime,
    CodecId.HvbSoc:                CodecHvbSoc,
    CodecId.HvbSocD:               CodecHvbSocD,
    CodecId.HvbEte:                CodecHvbEte,
    CodecId.HvbTemp:               CodecHvbTemp,
    CodecId.LvbSoc:                CodecLvbSoc,
    CodecId.LvbVoltage:            CodecLvbVoltage,
    CodecId.LvbCurrent:            CodecLvbCurrent,
    CodecId.HvbVoltage:            CodecHvbVoltage,
    CodecId.HvbCurrent:            CodecHvbCurrent,
    CodecId.ChargerStatus:         CodecChargerStatus,
    CodecId.EvseType:              CodecEvseType,
    CodecId.EvseDigitalMode:       CodecEvseDigitalMode,
}