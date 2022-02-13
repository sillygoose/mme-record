import logging
from time import time, sleep

from threading import Thread
from queue import Empty, Full, Queue
from typing import List
import json
from config.configuration import Configuration

from did_manager import DIDManager
from state_engine import initialize_did_cache, get_did_cache, set_did_cache

from record_filemgr import RecordFileManager
from state_manager import StateManager
from influxdb import influxdb_connect, influxdb_disconnect, influxdb_write_record
from exceptions import RuntimeError

_LOGGER = logging.getLogger('mme')


class RecordStateManager(StateManager):
    """
        config:                 dictionary of YAML file settings
        request_queue:          queue to place ReadDID service requests
        response_queue:         queue to retrieve ReadDID responses
    """
    def __init__(self, config: Configuration, request_queue: Queue, response_queue: Queue) -> None:
        super().__init__(config)
        self._exit_requested = False
        self._request_queue = request_queue
        self._response_queue = response_queue
        self._did_manager = DIDManager()
        sync_queue = Queue()
        self._request_thread = Thread(target=self._request_task, args=(sync_queue,), name='state_request')
        self._response_thread = Thread(target=self._response_task, args=(sync_queue,), name='state_response')
        self._file_manager = RecordFileManager(config.record)
        initialize_did_cache()
        influxdb_connect(config.influxdb2)

    def start(self) -> List[Thread]:
        super().start()
        self._exit_requested = False
        self._file_manager.start()
        self._request_thread.start()
        self._response_thread.start()
        return [self._request_thread, self._response_thread]

    def stop(self) -> None:
        super().stop()
        influxdb_disconnect()
        self._file_manager.stop()
        self._exit_requested = True
        if self._request_thread.is_alive():
            self._request_thread.join()
        if self._response_thread.is_alive():
            self._response_thread.join()

    def _request_task(self, sync_queue: Queue) -> None:
        # Steps done in _request_task:
        #   - get a command set
        #   - wait until it ready to fire
        #   - add the command set back if runs at intervals
        #   - wait for command set to execute
        try:
            while self._exit_requested == False:
                trigger_at = None
                while trigger_at is None:
                    # get a command set
                    try:
                        with self._command_queue_lock:
                            trigger_at, period, module_list = self._command_queue.get_nowait()
                    except Empty:
                        if self._exit_requested == True:
                            return
                        sleep(0.05)
                        self._load_queue()
                        continue

                    # wait until it ready to send to the request queue
                    current_time = time()
                    if current_time < trigger_at:
                        sleep(trigger_at - current_time)
                    try:
                        self._request_queue.put(module_list)
                    except Full:
                        _LOGGER.error(f"no space in the request queue")
                        self._exit_requested = True
                        return

                    # add the command set back if runs at intervals
                    if self._putback_enabled and period > 0:
                        with self._command_queue_lock:
                            try:
                                self._command_queue.put_nowait((time() + period, period, module_list))
                                self._command_queue.task_done()
                            except Full:
                                _LOGGER.error(f"no space in the command queue")
                                self._exit_requested = True
                                return

                    # wait for command set to be returned and processed
                    got_sync = False
                    while not got_sync:
                        try:
                            got_sync = sync_queue.get_nowait()
                            sync_queue.task_done()
                            #_LOGGER.debug("Command set completed processing")
                            break
                        except Empty:
                            if self._exit_requested == True:
                                return
                            sleep(0.05)
                            continue

        except RuntimeError:
            raise

    def _response_task(self, sync_queue: Queue) -> None:
        # Steps done in _response_task:
        #   - get the responses from the command set
        #   - process responses
        #   - update the vehicle state
        try:
            while self._exit_requested == False:
                try:
                    responses = self._response_queue.get(timeout=0.5)
                    sync_queue.put(True)
                except Empty:
                    if self._exit_requested == True:
                        return
                    continue

                for response_record in responses:
                    arbitration_id = response_record.get('arbitration_id')
                    response = response_record.get('response')
                    if response.positive == False and response.invalid_reason == 'request timed out':
                        did_list = response_record.get('did_list')
                        current_time = time()
                        for did_id in did_list:
                            key = f"{arbitration_id:04X}:{did_id:04X}"
                            states = self._did_manager.did_states(did_id)
                            _, packing_length = self._did_manager.did_packing(did_id)
                            for state in states:
                                default_value = state.get('default_value', None)
                                if default_value is None:
                                    break
                                payload = []
                                for _ in range(packing_length):
                                    payload.append(default_value)
                                state_details = {'time': current_time, 'arbitration_id': arbitration_id, 'arbitration_id_hex': f"{arbitration_id:04X}", 'did_id': did_id, 'did_id_hex': f"{did_id:04X}", 'payload': payload}
                                if get_did_cache(key) is None or get_did_cache(key) != payload:
                                    set_did_cache(key, payload)
                                    self._file_manager.write_record(state_details)
                                    if codec := self._codec_manager.codec(did_id):
                                        decoded = codec.decode(None, bytearray(payload))
                                        _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: {decoded.get('decoded')} (default value)")
                                    influxdb_state_data = self.update_vehicle_state(state_details)
                                    influxdb_write_record(influxdb_state_data)
                        continue

                    for did_id in response.service_data.values:
                        key = f"{arbitration_id:04X}:{did_id:04X}"
                        payload = response.service_data.values[did_id].get('payload')
                        current_time = time()
                        state_details = {'time': current_time, 'arbitration_id': arbitration_id, 'arbitration_id_hex': f"{arbitration_id:04X}", 'did_id': did_id, 'did_id_hex': f"{did_id:04X}", 'payload': list(payload)}
                        if get_did_cache(key) is None or get_did_cache(key) != payload:
                            set_did_cache(key, payload)
                            self._file_manager.write_record(state_details)
                            _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: {response.service_data.values[did_id].get('decoded')}")
                            influxdb_state_data = self.update_vehicle_state(state_details)
                            influxdb_write_record(influxdb_state_data)
                self._update_state_machine()
                self._response_queue.task_done()

        except RuntimeError:
            raise

    def _write_state_definition(self, state_dids: List, file: str) -> None:
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
