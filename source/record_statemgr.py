import logging
from time import time, sleep

from threading import Thread
from queue import Empty, Full, Queue
from typing import List
import json
from config.configuration import Configuration

from did_manager import DIDManager

from record_filemgr import RecordFileManager
from state_manager import StateManager
from influxdb import InfluxDB
from exceptions import SigTermCatcher


_LOGGER = logging.getLogger('mme')


class RecordStateManager(StateManager):
    """
        config:                 dictionary of YAML file settings
        request_queue:          queue to place ReadDID service requests
        response_queue:         queue to retrieve ReadDID responses
    """
    def __init__(self, config: Configuration, request_queue: Queue, response_queue: Queue) -> None:
        super().__init__()
        self._exit_requested = False
        self._request_queue = request_queue
        self._response_queue = response_queue
        self._did_manager = DIDManager()
        sync_queue = Queue()
        self._request_thread = Thread(target=self._request_task, args=(sync_queue,), name='state_request')
        self._response_thread = Thread(target=self._response_task, args=(sync_queue,), name='state_response')
        self._file_manager = RecordFileManager(config.record)
        self._influxdb = InfluxDB(config.influxdb2)
        self._did_state_cache = {}

    def start(self) -> List[Thread]:
        super().start()
        self._influxdb.start()
        self._exit_requested = False
        self._sigterm_catcher = SigTermCatcher(self._sigterm)
        self._file_manager.start()
        self._request_thread.start()
        self._response_thread.start()
        return [self._request_thread, self._response_thread]

    def stop(self) -> None:
        super().stop()
        self._influxdb.stop()
        self._file_manager.stop()
        self._exit_requested = True
        if self._request_thread.is_alive():
            self._request_thread.join()
        if self._response_thread.is_alive():
            self._response_thread.join()

    def _sigterm(self) -> None:
        self.stop()

    def _request_task(self, sync_queue: Queue) -> None:
        try:
            while self._exit_requested == False:
                trigger_at = 0
                while trigger_at == 0:
                    try:
                        with self._command_queue_lock:
                            trigger_at, period, module_list = self._command_queue.get_nowait()
                    except Empty:
                        if self._exit_requested == False:
                            sleep(0.05)
                            continue
                        return

                try:
                    current_time = time()
                    if current_time < trigger_at:
                        sleep(trigger_at - current_time)
                    self._request_queue.put(module_list)
                    with self._command_queue_lock:
                        try:
                            self._command_queue.put_nowait((time() + period, period, module_list))
                            self._command_queue.task_done()
                        except Full:
                            _LOGGER.error(f"no space in the command queue")
                            self._exit_requested = True
                            return

                    got_sync = False
                    while not got_sync:
                        try:
                            got_sync = sync_queue.get_nowait()
                            sync_queue.task_done()
                        except Empty:
                            if self._exit_requested == False:
                                sleep(0.05)
                                continue
                            return

                except Full:
                    _LOGGER.error(f"no space in the request queue")
                    self._exit_requested = True

        except RuntimeError:
            raise

    def _response_task(self, sync_queue: Queue) -> None:
        try:
            while self._exit_requested == False:
                try:
                    responses = self._response_queue.get(timeout=0.5)
                    sync_queue.put(True)
                except Empty:
                    if self._exit_requested == False:
                        continue
                    return

                for response_record in responses:
                    arbitration_id = response_record.get('arbitration_id')
                    response = response_record.get('response')
                    if response.positive == False:
                        did_list = response_record.get('did_list')
                        state_details = {'type': 'NegativeResponse', 'time': round(time(), 6), 'arbitration_id': arbitration_id, 'arbitration_id_hex': f"{arbitration_id:04X}", 'did_list': did_list}
                        self.update_vehicle_state(state_details)
                        _LOGGER.debug(f"The request from {arbitration_id:04X} returned the following response: {response.invalid_reason}")
                        continue

                    for did_id in response.service_data.values:
                        key = f"{arbitration_id:04X} {did_id:04X}"
                        payload = response.service_data.values[did_id].get('payload')
                        current_time = time()
                        state_details = {'time': current_time, 'arbitration_id': arbitration_id, 'arbitration_id_hex': f"{arbitration_id:04X}", 'did_id': did_id, 'did_id_hex': f"{did_id:04X}", 'payload': list(payload)}
                        if self._did_state_cache.get(key, None) is None or self._did_state_cache.get(key).get('payload', None) != payload:
                            self._did_state_cache[key] = {'time': round(current_time, 6), 'payload': payload}
                            self._file_manager.write_record(state_details)
                            _LOGGER.debug(f"{arbitration_id:04X}/{did_id:04X}: {response.service_data.values[did_id].get('decoded')}")
                        influxdb_state_data = self.update_vehicle_state(state_details)
                        self._influxdb.write_record(influxdb_state_data)
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
