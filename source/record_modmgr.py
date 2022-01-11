import logging
import json

from typing import List

import isotp
from udsoncan.connections import PythonIsoTpConnection
from can.interfaces.socketcan import SocketcanBus

from module_manager import ModuleManager


_LOGGER = logging.getLogger('mme')


class RecordModuleManager(ModuleManager):

    isotp_params = {
        'stmin' : 2,                               # Will request the sender to wait 2ms between consecutive frame. 0-127ms or 100-900ns with values from 0xF1-0xF9
        'blocksize' : 8,                           # Request the sender to send 8 consecutives frames before sending a new flow control message
        'wftmax' : 0,                              # Number of wait frame allowed before triggering an error
        'tx_data_length' : 8,                      # Link layer (CAN layer) works with 8 byte payload (CAN 2.0)
        'tx_data_min_length' : 8,                  # Minimum length of CAN messages. When different from None, messages are padded to meet this length. Works with CAN 2.0 and CAN FD.
        'tx_padding' : 0x00,                       # Will pad all transmitted CAN messages with byte 0x00.
        'rx_flowcontrol_timeout' : 2000,           # Triggers a timeout if a flow control is awaited for more than 1000 milliseconds
        'rx_consecutive_frame_timeout' : 2000,     # Triggers a timeout if a consecutive frame is awaited for more than 1000 milliseconds
        'squash_stmin_requirement' : False,        # When sending, respect the stmin requirement of the receiver. If set to True, go as fast as possible.
        'max_frame_size' : 4095                    # Limit the size of receive frame.
    }

    def __init__(self, config: dict) -> None:
        self._bus0 = None
        self._bus1 = None
        self._channel = None
        isotp_timeout = config.get('isotp_timeout', 2.0)
        RecordModuleManager.isotp_params['rx_flowcontrol_timeout'] = int(isotp_timeout * 1000)
        RecordModuleManager.isotp_params['rx_consecutive_frame_timeout'] = int(isotp_timeout * 1000)
        super().__init__(config)

    def start(self) -> None:
        self._bus0 = SocketcanBus(channel='can0')
        self._bus1 = SocketcanBus(channel='can1')
        self._isotp_connections = {}
        for module in self._modules:
            module_name = module.get('name')
            channel = module.get('channel')
            arbitration_id = module.get('arbitration_id')
            enable = module.get('enable')
            _LOGGER.debug(f"Processing module {module}")
            if enable:
                tp_addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=arbitration_id, rxid=arbitration_id + 0x8)
                bus = self._bus0 if channel == 'can0' else self._bus1
                stack = isotp.CanStack(bus=bus, address=tp_addr, params=RecordModuleManager.isotp_params)
                self._isotp_connections[module_name] = PythonIsoTpConnection(stack)
                _LOGGER.debug(f"Added module {module} to RecordModuleManager")

    def stop(self) -> None:
        if self._bus0:
            self._bus0.shutdown()
            self._bus0 = None
        if self._bus1:
            self._bus1.shutdown()
            self._bus1 = None

    def name(self) -> str:
        return self._name

    def channel(self) -> str:
        return self._channel

    def arbitration_id(self) -> int:
        return self._rxid

    def connection(self, name: str) -> PythonIsoTpConnection:
        return self._isotp_connections.get(name, None)

    def modules(self) -> List[dict]:
        return self._modules
