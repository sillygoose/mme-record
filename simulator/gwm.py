import time
import struct
import logging

import isotp
from can.interfaces.socketcan import SocketcanBus

from pid import PID
from can_module import CanModule


_LOGGER = logging.getLogger('mme')


class PID_411F(PID):
    def __init__(self) -> None:
        self._keystate = 3
        super().__init__(0x411F, 'KeyState')

    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

    def response(self) -> bytearray:
        return struct.pack('>BHB', 0x62, self._id, self._keystate)


class GWM(CanModule):
    pids = {
        0x411F: PID_411F(),     ### right?
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
        super().__init__('GWM', 'can0', 0x716, self._pid_task)

    def start(self) -> None:
        _LOGGER.info(f"Starting CanModule {self._name} on channel {self._channel} with address {self._rxid:03X}")
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=self._rxid, txid=self._txid)
        self._bus = SocketcanBus(channel=self._channel)
        self._stack = isotp.CanStack(bus=self._bus, address=addr, error_handler=self.error_handler, params=GWM.isotp_params)
        super().start()

    def _pid_task(self):
        self._stack.process()
        if self._stack.available():
            payload = self._stack.recv()
            service, pid = struct.unpack('>BH', payload)
            if service == 0x22:
                handler = GWM.pids.get(pid, None)
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
        _LOGGER.error('%s IsoTp error happened : %s - %s' % (self._name, error.__class__.__name__, str(error)))

    def stop(self) -> None:
        _LOGGER.info(f"Stopping CanModule {self._name}")
        self._bus.shutdown()
        super().stop()

    def shutdown(self):
        super().shutdown()