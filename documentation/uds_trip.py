# UDS trip logging

import os
import sys
import struct
import logging
import binascii
from time import time, sleep
import struct
import json

from udsoncan.connections import PythonIsoTpConnection
from udsoncan.client import Client
import udsoncan.configs
from udsoncan.exceptions import *

from can.interfaces.socketcan import SocketcanBus
import isotp

logger = logging.getLogger('mach-e')
logger.setLevel(logging.INFO)


class NullCodec(udsoncan.DidCodec):
    def encode(self, val):
        return struct.pack('<L', val) # Little endian, 32 bit value

    def decode(self, payload):
        return {'payload': payload, 'decoded': binascii.hexlify(payload, sep=' ')}

    def __len__(self):
        raise udsoncan.DidCodec.ReadAllRemainingData


class CodecKeyState(udsoncan.DidCodec):
    def encode(self, val):
        return val

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


class CodecEVSEDigitalMode(udsoncan.DidCodec):
    def encode(self, val):
        return val

    def decode(self, payload):
        digital_mode = struct.unpack('>B', payload)
        digital_modes = { 0: 'None', 1: 'DCE-', 2: 'DC-P', 3: 'DCEP', 4: 'ACE-', 5: 'AC-P', 6: 'ACEP', 7: 'Rst', 8: 'Off', 9: 'Est', 10: 'FAIL' }
        mode = digital_modes.get(digital_mode[0], "???")
        states = [{'evse_digital_mode': digital_mode}]
        return {'payload': payload, 'states': states, 'decoded': ('EVSE digital mode: ' + mode)}

    def __len__(self):
        return 1


class CodecGearDisplayed(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
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


class CodecGearCommanded(udsoncan.DidCodec):
    def encode(self, val):
        return val

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


class CodecGPS(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
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


class CodecOdometer(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
    def decode(self, payload):
        odometer_high, odometer_low = struct.unpack('>HB', payload)
        odometer = (odometer_high * 256 + odometer_low) * 0.1
        states = [{'odometer': odometer}]
        return {'payload': payload, 'states': states, 'decoded': f"Odometer: {odometer:.1f} km"}

    def __len__(self):
        return 3


class CodecHiresSpeed(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
    def decode(self, payload):
        hires_speed = struct.unpack('>H', payload)
        speed = hires_speed[0] / 128.0
        states = [{'speed': speed}]
        return {'payload': payload, 'states': states, 'decoded': f"Speed: {speed:.0f} kph"}

    def __len__(self):
        return 2


class CodecExteriorTemp(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
    def decode(self, payload):
        temp = struct.unpack('>B', payload)
        temp = temp[0] - 40
        states = [{'ext_temp': temp}]
        return {'payload': payload, 'states': states, 'decoded': f"Exterior temperature is {temp}°C"}

    def __len__(self):
        return 1


class CodecInteriorTemp(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
    def decode(self, payload):
        temp = struct.unpack('>B', payload)
        temp = temp[0] - 40
        states = [{'int_temp': temp}]
        return {'payload': payload, 'states': states, 'decoded': f"Interior temperature is {temp}°C"}

    def __len__(self):
        return 1


class CodecTime(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
    def decode(self, payload):
        car_time = struct.unpack('>L', payload)
        car_time = car_time[0] * 0.1
        states = [{'time': car_time}]
        return {'payload': payload, 'states': states, 'decoded': f"MME time is {car_time:.1f} s"}

    def __len__(self):
        return 4


class CodecHvbSoc(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
    def decode(self, payload):
        soc = struct.unpack('>H', payload)
        soc = soc[0] * 0.002
        states = [{'soc': soc}]
        return {'payload': payload, 'states': states, 'decoded': f"Internal SOC is {soc:.3f}%"}

    def __len__(self):
        return 2


class CodecHvbSocD(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
    def decode(self, payload):
        soc_displayed = struct.unpack('>B', payload)
        soc_displayed = soc_displayed[0] * 0.5
        states = [{'soc_displayed': soc_displayed}]
        return {'payload': payload, 'states': states, 'decoded': f"Displayed SOC is {soc_displayed:.0f}%"}

    def __len__(self):
        return 1


class CodecHvbEte(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
    def decode(self, payload):
        energyToEmpty = struct.unpack('>H', payload)
        energyToEmpty = energyToEmpty[0] * 0.002
        states = [{'HVBete': energyToEmpty}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB energy to empty is {energyToEmpty:.3f} kWh"}

    def __len__(self):
        return 2


class CodecHvbTemp(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
    def decode(self, payload):
        temp = struct.unpack('>B', payload)
        temp = temp[0] - 50
        states = [{'hvb_temp': temp}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB temp is {temp}°C"}

    def __len__(self):
        return 1


class CodecLvbSoc(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
    def decode(self, payload):
        soc = struct.unpack('>B', payload)
        soc = soc[0]
        states = [{'lvb_soc': soc}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB SOC is {soc}%"}

    def __len__(self):
        return 1


class CodecLvbVoltage(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
    def decode(self, payload):
        # A*0.05+6
        voltage = struct.unpack('>B', payload)
        voltage = voltage[0] * 0.05 + 6.0
        states = [{'lvb_voltage': voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB voltage is {voltage:.2f} V"}

    def __len__(self):
        return 1

class CodecLvbCurrent(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
    def decode(self, payload):
        # A*0.05+6
        current = struct.unpack('>B', payload)
        current = current[0] - 127
        states = [{'lvb_current': current}]
        return {'payload': payload, 'states': states, 'decoded': f"LVB current is {current} A"}

    def __len__(self):
        return 1


class CodecHvbVoltage(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
    def decode(self, payload):
        voltage = struct.unpack('>H', payload)
        voltage = voltage[0] * 0.01
        states = [{'hvb_voltage': voltage}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB voltage is {voltage:.2f} V"}

    def __len__(self):
        return 2


class CodecHvbCurrent(udsoncan.DidCodec):
    # ((signed(A)*256)+B)*0.1
    def encode(self, val):
        return val
      
    def decode(self, payload):
        current_msb, current_lsb = struct.unpack('>bB', payload)
        current = (current_msb * 256 + current_lsb) * 0.1
        states = [{'hvb_current': current}]
        return {'payload': payload, 'states': states, 'decoded': f"HVB current is {current:.1f} A"}

    def __len__(self):
        return 2


class CodecChargerStatus(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
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


class CodecEvseType(udsoncan.DidCodec):
    def encode(self, val):
        return val
      
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


_TIMEOUT = 2.0
config = dict(udsoncan.configs.default_client_config)
config['request_timeout'] = _TIMEOUT
config['p2_timeout'] = _TIMEOUT
config['p2_star_timeout'] = _TIMEOUT
config['logger_name'] = 'mach-e'

isotp_params = {
   'stmin' : 2,                                             # Will request the sender to wait 4ms between consecutive frame. 0-127ms or 100-900ns with values from 0xF1-0xF9
   'blocksize' : 8,                                         # Request the sender to send 8 consecutives frames before sending a new flow control message
   'wftmax' : 0,                                            # Number of wait frame allowed before triggering an error
   'tx_data_length' : 8,                                    # Link layer (CAN layer) works with 8 byte payload (CAN 2.0)
   'tx_data_min_length' : 8,                                # Minimum length of CAN messages. When different from None, messages are padded to meet this length. Works with CAN 2.0 and CAN FD.
   'tx_padding' : 0x00,                                     # Will pad all transmitted CAN messages with byte 0x00.
   'rx_flowcontrol_timeout' : int(_TIMEOUT * 1000),         # Triggers a timeout if a flow control is awaited for more than 1000 milliseconds
   'rx_consecutive_frame_timeout' : int(_TIMEOUT * 1000),   # Triggers a timeout if a consecutive frame is awaited for more than 1000 milliseconds
   'squash_stmin_requirement' : False,                      # When sending, respect the stmin requirement of the receiver. If set to True, go as fast as possible.
   'max_frame_size' : 4095                                  # Limit the size of receive frame.
}

mach_e = [
    {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
            {'did': 0x411F, 'codec': CodecKeyState},            # Ignition state
        ]},
    {'module': 'SOBDM', 'address': 0x7E2, 'bus': 'can0', 'dids': [
            {'did': 0xDD00, 'codec': CodecTime},                # Time
            #{'did': 0xDD04, 'codec': CodecInteriorTemp},        # Interior temp
            {'did': 0xDD05, 'codec': CodecExteriorTemp},        # External temp
            {'did': 0x1E12, 'codec': CodecGearCommanded},       # Gear commanded
            #{'did': 0x48B7, 'codec': CodecEVSEDigitalMode},     # EVSE digital mode
        ]},
    {'module': 'APIM', 'address': 0x7D0, 'bus': 'can1', 'dids': [
            {'did': 0x8012, 'codec': CodecGPS},                 # GPS data
        ]},
    {'module': 'IPC', 'address': 0x720, 'bus': 'can1', 'dids': [
            {'did': 0x404C, 'codec': CodecOdometer},            # Odometer
            {'did': 0x6310, 'codec': CodecGearDisplayed},       # Gear displayed
        ]},
    {'module': 'PCM', 'address': 0x7E0, 'bus': 'can0', 'dids': [
            {'did': 0x1505, 'codec': CodecHiresSpeed},          # Speed
        ]},
    {'module': 'BECM', 'address': 0x7E4, 'bus': 'can0', 'dids': [
            {'did': 0x4801, 'codec': CodecHvbSoc},              # HVB SOC
            {'did': 0x4845, 'codec': CodecHvbSocD},             # HVB SOC displayed
            {'did': 0x4848, 'codec': CodecHvbEte},              # HVB Energy to empty
        ]},
    {'module': 'BECM', 'address': 0x7E4, 'bus': 'can0', 'dids': [
            {'did': 0x4800, 'codec': CodecHvbTemp},             # HVB temp
            {'did': 0x480D, 'codec': CodecHvbVoltage},          # HVB Voltage
            {'did': 0x48F9, 'codec': CodecHvbCurrent},          # HVB Current
        ]},
    {'module': 'BECM', 'address': 0x7E4, 'bus': 'can0', 'dids': [
        #    {'did': 0x484F, 'codec': CodecChargerStatus},       # Charger status
        #    {'did': 0x4851, 'codec': CodecEvseType},            # EVSE type
        ]},
    {'module': 'BCM', 'address': 0x726, 'bus': 'can0', 'dids': [
        #    {'did': 0x4028, 'codec': CodecLvbSoc},              # LVB State of Charge
        #    {'did': 0x402A, 'codec': CodecLvbVoltage},          # LVB Voltage
        #    {'did': 0x402B, 'codec': CodecLvbCurrent},          # LVB Current
        ]},
]


SHOW_NEGATIVE_RESPONSE_EXCEPTION = True
SHOW_TIMEOUT_EXCEPTION = True
_SLEEP = 2.0

DID_DATA = {}


def main():
    setup_logging()

    filename = f"trip2"
    dest_path = 'record'
    count = 0

    start_time = int(time())
    last_saved = start_time
    data_log = []
    first_pass = True
    logger.info(f"0000 0000 pass #1 started")

    bus0 = SocketcanBus(channel='can0') 
    bus1 = SocketcanBus(channel='can1') 
    
    module_connections = {}
    for module in mach_e:
        module_name = module.get('module')
        if module_connections.get(module_name, None):
            continue

        txid = module.get('address')
        tp_addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=txid, rxid=txid + 0x8)
        bus = bus0 if module.get('bus') == 'can0' else bus1
        stack = isotp.CanStack(bus=bus, address=tp_addr, params=isotp_params)
        conn = PythonIsoTpConnection(stack)
        module_connections[module_name] = conn

    try:
        while True:
            try:
                for module in mach_e:
                    module_name = module.get('module')
                    txid = module.get('address')
                    conn = module_connections.get(module_name)

                    did_list = []
                    data_identifiers = {}
                    for did_dict in module.get('dids'):
                        did = did_dict.get('did')
                        did_list.append(did)
                        data_identifiers[did] = did_dict.get('codec')
                    if len(did_list) == 0:
                        continue

                    config['data_identifiers'] = data_identifiers
                    with Client(conn, request_timeout=_TIMEOUT, config=config) as client:
                        key = ''
                        try:
                            response = client.read_data_by_identifier(did_list)
                            current_time = round(time() - start_time, ndigits=1)
                            for did in did_list:
                                payload = response.service_data.values[did].get('payload')
                                decoded = response.service_data.values[did].get('decoded')
                                key = f"{txid:04X} {did:04X}"
                                if DID_DATA.get(key, None) is None:
                                    DID_DATA[key] = payload
                                    logger.info(f"{key} {decoded}")
                                    data_log.append({'time': current_time, 'arbitration_id': txid, 'did': did, 'payload': list(payload)})
                                else:
                                    if DID_DATA.get(key) != payload:
                                        DID_DATA[key] = payload                           
                                        logger.info(f"{key} {decoded}")
                                        data_log.append({'time': current_time, 'arbitration_id': txid, 'did': did, 'payload': list(payload)})

                                states = response.service_data.values[did].get('states')
                                new_event = {'module': txid, 'did': did, 'states': states}

                        except ValueError as e:
                            logger.error(f"{txid:04X}: {e}")
                        except ConfigError as e:
                            logger.error(f"{txid:04X}: {e}")
                        except TimeoutException as e:
                            if SHOW_TIMEOUT_EXCEPTION:
                                logger.error(f"{txid:04X}: {e}")
                        except NegativeResponseException as e:
                            if SHOW_NEGATIVE_RESPONSE_EXCEPTION:
                                logger.error(f"{txid:04X}: {e}")
                        except UnexpectedResponseException as e:
                            logger.error(f"{txid:04X}: {e}")
                        except InvalidResponseException as e:
                            logger.error(f"{txid:04X}: {e}")
                        except Exception as e:
                            logger.error(f"Unexpected excpetion: {e}")

                if first_pass:
                    logger.info(f"0000 0000 pass #1 completed")
                    first_pass = False

                sleep(_SLEEP)

                if len(data_log):
                    now = int(time())
                    if (now - last_saved) > 20:
                        full_filename = f"{dest_path}/{filename}_{count:03d}.json"
                        json_data_log = json.dumps(data_log, indent = 4, sort_keys=False)
                        with open(full_filename, "w") as outfile:
                            outfile.write(json_data_log)
                        count += 1
                        data_log = []
                        last_saved = now

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.exception(f"Unexpected exception: {e}")
    finally:
        with open(filename, "a") as outfile:
            outfile.write('\n]')

        print("\nShutting down CAN buses")
        bus0.shutdown()
        bus1.shutdown()



def setup_logging():
    logging.getLogger('UdsClient[mach-e]').addHandler(logging.NullHandler())
    filename = os.path.expanduser('uds_trip.log')
    fh = logging.FileHandler(filename=filename, mode='w')
    formatter = logging.Formatter(fmt='%(asctime)s %(message)s')
    fh.setFormatter(formatter)
    fh.setLevel(logging.INFO)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)


if __name__ == "__main__":
    # make sure we can run this
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
        main()
    else:
        print("python 3.10 or better required")
