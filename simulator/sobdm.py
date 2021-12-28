import time
import struct
import logging

import isotp
from can.interfaces.socketcan import SocketcanBus

from pid import PID
from can_module import CanModule


_LOGGER = logging.getLogger('mme')


class PID_1E12(PID):
    def __init__(self) -> None:
        self._state = 50
        super().__init__(0x1E12, 'GearCommanded')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_4842(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x4842, 'HvbChargeCurrentRequested')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_4844(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x4844, 'HvbChargeVoltageRequested')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_484A(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x484A, 'ChargerOutputVoltage')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_484E(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x484E, 'ChargerInputPower')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_4850(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x4850, 'ChargerOutputCurrent')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_485E(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x485E, 'ChargerInputVoltage')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHH', 0x62, self._id, self._state)

class PID_485F(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x485F, 'ChargerInputCurrent')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_4860(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x4860, 'ChargerInputFrequency')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_4861(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x4861, 'ChargerPilotDutyCycle')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_48B6(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x48B6, 'ChargerPilotVoltage')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_48BC(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x48BC, 'HvbMaximumChargeCurrent')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHh', 0x62, self._id, self._state)

class PID_48C4(PID):
    def __init__(self) -> None:
        self._state = 0
        super().__init__(0x48C4, 'ChargerMaxPower')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHH', 0x62, self._id, self._state)

class PID_DD00(PID):
    def __init__(self) -> None:
        self._state = int(time.time())
        super().__init__(0xDD00, 'GlobalTime')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHI', 0x62, self._id, self._state)

class PID_DD04(PID):
    def __init__(self) -> None:
        self._state = 50
        super().__init__(0xDD04, 'InteriorTemp')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)

class PID_DD05(PID):
    def __init__(self) -> None:
        self._state = 50
        super().__init__(0xDD05, 'ExteriorTemp')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._state)


class SOBDM(CanModule):
    pids = {
        0x1E12: PID_1E12(),
        0x4842: PID_4842(),
        0x4844: PID_4844(),
        0x484A: PID_484A(),
        0x484E: PID_484E(),
        0x4850: PID_4850(),
        0x485E: PID_485E(),
        0x485F: PID_485F(),
        0x4860: PID_4860(),
        0x4861: PID_4861(),
        0x48B6: PID_48B6(),
        0x48BC: PID_48BC(),
        0x48C4: PID_48C4(),
        0xDD00: PID_DD00(),
        0xDD04: PID_DD04(),
        0xDD05: PID_DD05(),
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
        super().__init__('SOBDM', 'can0', 0x7E2, self._pid_task)

    def start(self) -> None:
        _LOGGER.info(f"Starting CanModule {self._name} on channel {self._channel} with address {self._rxid:03X}")
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=self._rxid, txid=self._txid)
        self._bus = SocketcanBus(channel=self._channel)
        self._stack = isotp.CanStack(bus=self._bus, address=addr, error_handler=self.error_handler, params=SOBDM.isotp_params)
        super().start()

    def _pid_task(self):
        self._stack.process()
        if self._stack.available():
            payload = self._stack.recv()
            service, pid = struct.unpack('>BH', payload)
            if service == 0x22:
                handler = SOBDM.pids.get(pid, None)
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
        logging.error('%s IsoTp error happened : %s - %s' % (self._name, error.__class__.__name__, str(error)))

    def stop(self) -> None:
        _LOGGER.info(f"Stopping CanModule {self._name}")
        self._bus.shutdown()
        super().stop()

    def shutdown(self):
        super().shutdown()