import time
import logging
import threading

import isotp
from can.interfaces.socketcan import SocketcanBus

from pid import PID


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


class CanModule:
    def __init__(self, name, channel, id, handler) -> None:
        self._name = name
        self._channel = channel
        self._rxid = id
        self._txid = id + 8
        self._hanlder = handler
        self._exit_requested = False

    def start(self) -> None:
        self._exit_requested = False
        self._thread = threading.Thread(target=self._thread_task)
        self._thread.start()

    def stop(self) -> None:
        self._exit_requested = True
        if self._thread.is_alive():
            self._thread.join()

    def _thread_task(self):
        while self._exit_requested == False:
            self._hanlder()

    def shutdown(self):
        self.stop()

    def name(self) -> str:
        return self._name

    def bus(self) -> str:
        return self._bus

    def id(self) -> int:
        return self._rxid
