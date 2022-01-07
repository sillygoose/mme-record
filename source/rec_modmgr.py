import logging
import json

from typing import List

import isotp
from udsoncan.connections import PythonIsoTpConnection
from can.interfaces.socketcan import SocketcanBus

#from exceptions import FailedInitialization


_LOGGER = logging.getLogger('mme')


class RecordModuleManager:

    isotp_timeout = 5.0
    isotp_params = {
        'stmin' : 2,                                                    # Will request the sender to wait 2ms between consecutive frame. 0-127ms or 100-900ns with values from 0xF1-0xF9
        'blocksize' : 8,                                                # Request the sender to send 8 consecutives frames before sending a new flow control message
        'wftmax' : 0,                                                   # Number of wait frame allowed before triggering an error
        'tx_data_length' : 8,                                           # Link layer (CAN layer) works with 8 byte payload (CAN 2.0)
        'tx_data_min_length' : 8,                                       # Minimum length of CAN messages. When different from None, messages are padded to meet this length. Works with CAN 2.0 and CAN FD.
        'tx_padding' : 0x00,                                            # Will pad all transmitted CAN messages with byte 0x00.
        'rx_flowcontrol_timeout' : int(isotp_timeout * 1000),           # Triggers a timeout if a flow control is awaited for more than 1000 milliseconds
        'rx_consecutive_frame_timeout' : int(isotp_timeout * 1000),     # Triggers a timeout if a consecutive frame is awaited for more than 1000 milliseconds
        'squash_stmin_requirement' : False,                             # When sending, respect the stmin requirement of the receiver. If set to True, go as fast as possible.
        'max_frame_size' : 4095                                         # Limit the size of receive frame.
    }

    _modules = None
    _modules_by_name = None
    _modules_by_id = None
    _isotp_connections = None

    def __init__(self, config: dict) -> None:
        self._config = config
        self._bus0 = None
        self._bus1 = None
        RecordModuleManager._modules = self._load_modules(file='json/mme_modules.json')
        RecordModuleManager._modules_by_name = self._modules_organized_by_name(RecordModuleManager._modules)
        RecordModuleManager._modules_by_id = self._modules_organized_by_id(RecordModuleManager._modules)

    def start(self) -> None:
        self._bus0 = SocketcanBus(channel='can0')
        self._bus1 = SocketcanBus(channel='can1')
        RecordModuleManager._isotp_connections = {}
        for module in RecordModuleManager._modules:
            name = module.get('name')
            channel = module.get('channel')
            arbitration_id = module.get('arbitration_id')
            enable = module.get('enable')
            _LOGGER.debug(f"Processing module {module}")
            if enable:
                tp_addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=arbitration_id, rxid=arbitration_id + 0x8)
                bus = self._bus0 if channel == 'can0' else self._bus1
                stack = isotp.CanStack(bus=bus, address=tp_addr, params=RecordModuleManager.isotp_params)
                RecordModuleManager._isotp_connections[name] = PythonIsoTpConnection(stack)
                _LOGGER.debug(f"Added module {module} to manager")

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

    def _modules_organized_by_name(self, modules: List[dict]) -> dict:
        modules_by_names = {}
        for module in modules:
            modules_by_names[module.get('name')] = module
        return modules_by_names

    def _modules_organized_by_id(self, modules: List[dict]) -> dict:
        modules_by_id = {}
        for module in modules:
            modules_by_id[module.get('arbitration_id')] = module
        return modules_by_id

    def _load_modules(self, file: str) -> dict:
        try:
            with open(file) as infile:
                modules = json.load(infile)
        except FileNotFoundError as e:
            raise RuntimeError(f"{e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON error in '{file}' at line {e.lineno}")
        enabled_modules = []
        for module in modules:
            enable = module.get('enable', False)
            if enable:
                enabled_modules.append(module)
        return enabled_modules

    def _dump_modules(self, file: str, modules: dict) -> None:
        json_modules = json.dumps(modules, indent = 4, sort_keys=False)
        with open(file, "w") as outfile:
            outfile.write(json_modules)


    # Static
    def connection(name: str) -> PythonIsoTpConnection:
        return RecordModuleManager._isotp_connections.get(name, None)

    def modules() -> List[dict]:
        return RecordModuleManager._modules

    def arbitration_id(name: str) -> int:
        module_record = RecordModuleManager._modules_by_name.get(name, None)
        return module_record.get('arbitration_id')

    def module_name(arbitration_id: int) -> str:
        module_record = RecordModuleManager._modules_by_id.get(arbitration_id, None)
        return module_record.get('name')
