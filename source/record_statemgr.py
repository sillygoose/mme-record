import logging
from time import time, sleep

from threading import Thread
from queue import Empty, Full, Queue, PriorityQueue
from typing import List
import json

from did_manager import DIDManager

from record_filemgr import RecordFileManager
#from codec_manager import *
from state_manager import StateManager

_LOGGER = logging.getLogger('mme')


class RecordStateManager(StateManager):
    """
        config:                 dictionary of YAML file settings
        request_queue:          queue to place ReadDID service requests
        response_queue:         queue to retrieve ReadDID responses
    """
    def __init__(self, config: dict, request_queue: Queue, response_queue: Queue) -> None:
        super().__init__(config)
        self._exit_requested = False
        self._request_queue = request_queue
        self._response_queue = response_queue
        self._did_manager = DIDManager(config=config)
        sync_queue = Queue()
        self._request_thread = Thread(target=self._request_task, args=(sync_queue,), name='state_request')
        self._response_thread = Thread(target=self._response_task, args=(sync_queue,), name='state_response')
        self._file_manager = RecordFileManager(config)
        self._did_state_cache = {}
        self._command_queue = PriorityQueue()

    def start(self) -> List[Thread]:
        self._exit_requested = False
        self._current_state_definition = self._load_state_definition(self.get_current_state_file())
        self._load_queue(self._current_state_definition)
        self._request_thread.start()
        self._response_thread.start()
        return [self._request_thread, self._response_thread, self._file_manager.start()]

    def stop(self) -> None:
        self._file_manager.stop()
        self._exit_requested = True
        if self._request_thread.is_alive():
            self._request_thread.join()
        if self._response_thread.is_alive():
            self._response_thread.join()

    def _load_queue(self, module_read_commands: List[dict]) -> None:
        for module in module_read_commands:
            enable = module.get('enable', True)
            if enable:
                period = module.get('period', 5)
                payload = (time(), period, [module])
                self._command_queue.put(payload)

    def _request_task(self, sync_queue: Queue) -> None:
        try:
            while self._exit_requested == False:
                try:
                    trigger_at, period, module_list = self._command_queue.get()
                    current_time = round(time(), 2)
                    if current_time < trigger_at:
                        sleep(trigger_at - current_time)
                    self._request_queue.put(module_list)
                    current_time = round(time(), 2)
                    self._command_queue.put((current_time + period, period, module_list))
                    sync_queue.get()
                except Full:
                    _LOGGER.error(f"no space in the request queue")
                    self._exit_requested = True
        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return

    def _response_task(self, sync_queue: Queue) -> None:
        try:
            while self._exit_requested == False:
                try:
                    responses = self._response_queue.get(timeout=0.5)
                    sync_queue.put(1)
                except Empty:
                    if self._exit_requested == False:
                        continue
                    return

                for response_record in responses:
                    arbitration_id = response_record.get('arbitration_id')
                    response = response_record.get('response')
                    if response.positive == False:
                        did_list = response_record.get('did_list')
                        _LOGGER.debug(f"The request from {arbitration_id:04X} returned the following response: {response.invalid_reason}")
                        details = {'type': 'NegativeResponse', 'time': round(time(), 2), 'arbitration_id': arbitration_id, 'arbitration_id_hex': f"{arbitration_id:04X}", 'did_list': did_list}
                        self._state_function(details)
                        continue

                    for did_id in response.service_data.values:
                        key = f"{arbitration_id:04X} {did_id:04X}"
                        payload = response.service_data.values[did_id].get('payload')
                        if self._did_state_cache.get(key, None) is None or self._did_state_cache.get(key).get('payload', None) != payload:
                            current_time = round(time(), 2)
                            self._did_state_cache[key] = {'time': current_time, 'payload': payload}
                            details = {'time': current_time, 'arbitration_id': arbitration_id, 'arbitration_id_hex': f"{arbitration_id:04X}", 'did_id': did_id, 'did_id_hex': f"{did_id:04X}", 'payload': list(payload)}
                            self._file_manager.put(details)
                            self._state_function(details)
                        _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: {response.service_data.values[did_id].get('decoded')}")

        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return

    def _write__state_definition(self, state_dids: List, file: str) -> None:
        output_modules = []
        for module in state_dids:
            module_name = module.get('module')
            arbitration_id = module.get('address')
            output_dids = []
            dids = module.get('dids')
            for did in dids:
                did_id = did.get('did_id')
                name = self._did_manager.did_name(did_id)
                codec_id = did_id
                output_dids.append({'did_name': name, 'did_id': did_id, 'did_id_hex': f"{did_id:04X}", 'codec_id': codec_id})
            new_module = {'module': module_name, 'arbitration_id': arbitration_id, 'arbitration_id_hex': f"{arbitration_id:04X}", 'dids': output_dids}
            output_modules.append(new_module)
        json_dids = json.dumps(output_modules, indent = 4, sort_keys=False)
        with open(file, "w") as outfile:
            outfile.write(json_dids)

    def _load_state_definition(self, file: str) -> List[dict]:
        with open(file) as infile:
            try:
                state_definition = json.load(infile)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON error in '{file}' at line {e.lineno}")
            except FileNotFoundError as e:
                raise RuntimeError(f"{e}")

        for module in state_definition:
            dids = module.get('dids')
            for did in dids:
                codec_id = did.get('codec_id')
                codec = self._codec_manager.codec(codec_id)
                did['codec'] = codec
        return state_definition
