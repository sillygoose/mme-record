import time
import logging
from threading import Thread
from queue import Queue
import struct
import json

from typing import List, Any

import isotp
from can.interfaces.socketcan import SocketcanBus

from pb_did import PlaybackDID
from exceptions import FailedInitialization


_LOGGER = logging.getLogger('mme')


class PlaybackModuleManager:

    _modules = None
    _modules_by_name = None
    _modules_by_id = None

    def modules() -> List[dict]:
        return PlaybackModuleManager._modules

    def module(value: Any) -> dict:
        if type(value) is str:
            return PlaybackModuleManager._modules_by_name.get(value, None)
        elif type(value) is int:
            return PlaybackModuleManager._modules_by_id.get(value, None)
        return None

    def arbitration_id(name: str) -> int:
        module_record = PlaybackModuleManager._modules_by_name.get(name, None)
        return module_record.get('arbitration_id')

    def module_name(arbitration_id: int) -> str:
        module_record = PlaybackModuleManager._modules_by_id.get(arbitration_id, None)
        return module_record.get('name')

    def __init__(self, config: dict) -> None:
        self._config = config
        PlaybackModuleManager._modules = self._load_modules(file='json/mme_modules.json')
        PlaybackModuleManager._modules_by_name = self._modules_organized_by_name(PlaybackModuleManager._modules)
        PlaybackModuleManager._modules_by_id = self._modules_organized_by_id(PlaybackModuleManager._modules)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

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
        with open(file) as infile:
            try:
                modules = json.load(infile)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON error in '{file}' at line {e.lineno}")
        return modules

    def _dump_modules(self, file: str, modules: dict) -> None:
        json_modules = json.dumps(modules, indent = 4, sort_keys=False)
        with open(file, "w") as outfile:
            outfile.write(json_modules)


class PlaybackModule:

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

    def __init__(self, name: str, arbitration_id: int, channel: str, event_queue: Queue, state_queue: Queue) -> None:
        module_lookup = PlaybackModuleManager.module(name)
        if module_lookup is None:
            raise FailedInitialization(f"The module '{name}' is not supported by Playback or cannot be created")

        self._name = name
        self._event_queue = event_queue
        self._state_queue = state_queue
        self._channel = channel
        self._rxid = arbitration_id
        self._txid = self._rxid + 8
        self._exit_requested = False
        self._bus = None
        self._stack = None
        self._did_thread = None
        self._dids = {}

    def start(self) -> List[Thread]:
        self._exit_requested = False
        _LOGGER.debug(f"Starting module '{self._name}' on channel '{self._channel}' with arbitration ID {self._rxid:03X}")
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=self._rxid, txid=self._txid)
        self._bus = SocketcanBus(channel=self._channel)
        self._stack = isotp.CanStack(bus=self._bus, address=addr, error_handler=self.error_handler, params=PlaybackModule.isotp_params)
        self._did_thread = Thread(target=self._did_task, name=self._name)
        self._did_thread.start()
        return [self._did_thread]

    def stop(self) -> None:
        _LOGGER.debug(f"Stopping module {self._name}")
        self._exit_requested = True
        if self._did_thread.is_alive():
            self._did_thread.join()
        if self._bus:
            self._bus.shutdown()
            self._bus = None

    def add_did(self, did: PlaybackDID) -> None:
        did_id = did.did_id()
        self._dids[did_id] = did

    def _did_task(self) -> None:
        while self._exit_requested == False:
            time.sleep(self._stack.sleep_time())
            self._stack.process()
            if self._stack.available():
                payload = self._stack.recv()
                service = struct.unpack_from('>B', payload)
                if service[0] == 0x22:
                    offset = 1
                    response = struct.pack('>B', 0x62)
                    while offset < len(payload):
                        did = struct.unpack_from('>H', payload, offset=offset)
                        offset += 2
                        did = did[0]
                        response += struct.pack('>H', did)
                        did_handler = self._dids.get(did, None)
                        if did_handler is None:
                            response = struct.pack('>BBB', 0x7F, 0x22, 0x31)
                            break
                        else:
                            response += did_handler.response()

                    while self._stack.transmitting():
                        self._stack.process()
                        time.sleep(self._stack.sleep_time())
                    self._stack.send(response)

            if not self._event_queue.empty():
                event = self._event_queue.get(block=False)
                _LOGGER.debug(f"Dequeued event {event} on queue {PlaybackModuleManager.module_name(event.get('arbitration_id'))}")
                did_handler = self._dids.get(event.get('did'), None)
                if did_handler:
                    did_handler.new_event(event)
                    self._state_queue.put(event)

    def error_handler(self, error) -> None:
        _LOGGER.error('%s IsoTp error happened : %s - %s' % (self._name, error.__class__.__name__, str(error)))

    def name(self) -> str:
        return self._name

    def channel(self) -> str:
        return self._channel

    def arbitration_id(self) -> int:
        return self._rxid

    def dids(self) -> List[PlaybackDID]:
        return self._dids
