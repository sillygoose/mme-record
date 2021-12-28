import time
import struct
import logging

import isotp
from can.interfaces.socketcan import SocketcanBus

from pid import PID
from can_module import CanModule


class PID_4800(PID):
    def __init__(self) -> None:
        self._state = 0x40
        super().__init__(0x4800, 'HvbTemp')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_4801(PID):
    def __init__(self) -> None:
        self._state = 0x7A86
        super().__init__(0x4801, 'HvbSoc')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHH', 0x62, self._id, self._state)

class PID_480D(PID):
    def __init__(self) -> None:
        self._state = 0x8ABD
        super().__init__(0x480D, 'HvbV')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHH', 0x62, self._id, self._state)

class PID_4845(PID):
    def __init__(self) -> None:
        self._state = 0x84
        super().__init__(0x4845, 'HvbSocD')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_4848(PID):
    def __init__(self) -> None:
        self._state = 0x63C5
        super().__init__(0x4848, 'EnergyToEmpty')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHH', 0x62, self._id, self._state)

class PID_484F(PID):
    def __init__(self) -> None:
        self._state = 0x03
        super().__init__(0x484F, 'ChargerStatus')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_4851(PID):
    def __init__(self) -> None:
        self._state = 0x06
        super().__init__(0x4851, 'EvseType')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_48F9(PID):
    def __init__(self) -> None:
        self._state = 0x0052
        super().__init__(0x48F9, 'HvbA')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_48FB(PID):
    def __init__(self) -> None:
        self._state = -1
        super().__init__(0x48FB, 'ChargePowerLimit')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_490C(PID):
    def __init__(self) -> None:
        self._state = 0xC8
        super().__init__(0x490C, 'HvbSoh')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)


class BECM(CanModule):
    pids = {
        0x4800: PID_4800(),
        0x4801: PID_4801(),
        0x480D: PID_480D(),
        0x4845: PID_4845(),
        0x4848: PID_4848(),
        0x484F: PID_484F(),
        0x4851: PID_4851(),
        0x48F9: PID_48F9(),
        0x48FB: PID_48FB(),
        0x490C: PID_490C(),
    }

    _TIMEOUT = 5.0
    isotp_params = {
        'stmin' : 32,                                            # Will request the sender to wait 32ms between consecutive frame. 0-127ms or 100-900ns with values from 0xF1-0xF9
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

    def __init__(self) -> None:
        super().__init__('BECM', 'can0', 0x7E4, self._pid_task)

    def start(self) -> None:
        print(f"Starting CanModule {self._name} on channel {self._channel} with address {self._rxid:03X}")
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=self._rxid, txid=self._txid)
        self._bus = SocketcanBus(channel=self._channel)
        self._stack = isotp.CanStack(bus=self._bus, address=addr, error_handler=self.error_handler, params=BECM.isotp_params)
        super().start()

    def _pid_task(self):
        self._stack.process()
        if self._stack.available():
            payload = self._stack.recv()
            service, pid = struct.unpack('>BH', payload)
            if service == 0x22:
                handler = BECM.pids.get(pid, None)
                if handler is None:
                    response = struct.pack('>BBB', 0x7F, 0x22, 0x31)
                else:
                    response = handler.response()
                while self._stack.transmitting():
                    self._stack.process()
                    time.sleep(self._stack.sleep_time())
                self._stack.send(response)
        time.sleep(self._stack.sleep_time())

    def error_handler(self, error):
        logging.warning('%s IsoTp error happened : %s - %s' % (self._name, error.__class__.__name__, str(error)))

    def stop(self) -> None:
        print(f"Stopping CanModule {self._name}")
        self._bus.shutdown()
        super().stop()

    def shutdown(self):
        super().shutdown()