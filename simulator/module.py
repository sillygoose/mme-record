import time
import logging
import threading
import struct
from typing import List

import isotp
from can.interfaces.socketcan import SocketcanBus

from simulator.pid import PID


_LOGGER = logging.getLogger('mme')

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


class Module:
    def __init__(self, name: str, channel: str, arbitration_id: int, pids: List[PID]) -> None:
        self._name = name
        self._channel = channel
        self._rxid = arbitration_id
        self._txid = arbitration_id + 8
        self._exit_requested = False
        self._bus = None
        self._stack = None
        self._pids = {}
        for pid in pids:
            self._pids[pid.id()] = pid

    def start(self) -> None:
        self._exit_requested = False
        _LOGGER.info(f"Starting module {self._name} on channel {self._channel} with arbitration ID {self._rxid:03X}")
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=self._rxid, txid=self._txid)
        self._bus = SocketcanBus(channel=self._channel)
        self._stack = isotp.CanStack(bus=self._bus, address=addr, error_handler=self.error_handler, params=isotp_params)
        self._thread = threading.Thread(target=self._pid_task)
        self._thread.start()

    def stop(self) -> None:
        _LOGGER.info(f"Stopping module {self._name}")
        self._exit_requested = True
        if self._thread.is_alive():
            self._thread.join()
        if self._bus:
            self._bus.shutdown()
            self._bus = None

    def _pid_task(self) -> None:
        while self._exit_requested == False:
            time.sleep(self._stack.sleep_time())
            self._stack.process()
            if self._stack.available():
                payload = self._stack.recv()
                service, pid = struct.unpack('>BH', payload)
                if service == 0x22:
                    pid_handler = self._pids.get(pid, None)
                    if pid_handler is None:
                        response = struct.pack('>BBB', 0x7F, 0x22, 0x31)
                    else:
                        response = pid_handler.response()
                    while self._stack.transmitting():
                        self._stack.process()
                        time.sleep(self._stack.sleep_time())
                    self._stack.send(response)

    def error_handler(self, error) -> None:
        _LOGGER.error('%s IsoTp error happened : %s - %s' % (self._name, error.__class__.__name__, str(error)))

    def name(self) -> str:
        return self._name

    def channel(self) -> str:
        return self._channel

    def arbitration_id(self) -> int:
        return self._rxid

    def pids(self) -> List[PID]:
        return self._pids
