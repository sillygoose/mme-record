import logging
from typing import List

from  threading import Thread
from queue import Empty, Full, Queue

import udsoncan.configs
from udsoncan.client import Client
from udsoncan import Response
from udsoncan.exceptions import *

from record_modmgr import RecordModuleManager
from config.configuration import Configuration
from exceptions import SigTermCatcher


_LOGGER = logging.getLogger('mme')


class RecordCanbusManager:

    def __init__(self, config: Configuration, request_queue: Queue, response_queue: Queue, module_manager: RecordModuleManager) -> None:
        config_record = dict(config.record)
        self._module_manager = module_manager
        self.request_queue = request_queue
        self.response_queue = response_queue
        self._exit_requested = False
        self._did_read = config_record.get('did_read', 1)
        self._iso_tp_config = dict(udsoncan.configs.default_client_config)
        self._iso_tp_config['request_timeout'] = config_record.get('request_timeout', 1.0)
        self._iso_tp_config['p2_timeout'] = config_record.get('p2_timeout', 1.0)
        self._iso_tp_config['p2_star_timeout'] = config_record.get('p2_star_timeout', 1.0)
        self._iso_tp_config['logger_name'] = 'mme'

    def start(self) -> List[Thread]:
        self._exit_requested = False
        self._sigterm_catcher = SigTermCatcher(self._sigterm)
        self._thread = Thread(target=self._canbus_task, name='canbus_manager')
        self._thread.start()
        return [self._thread]

    def stop(self) -> None:
        self._exit_requested = True
        if self._thread.is_alive():
            self._thread.join()

    def _sigterm(self) -> None:
        self.stop()

    def _canbus_task(self) -> None:
        try:
            while self._exit_requested == False:
                try:
                    job = self.request_queue.get(block=True, timeout=None)
                except Empty:
                    _LOGGER.error(f"timeout on the request queue")
                    continue

                responses = []
                for module in job:
                    module_name = module.get('module')
                    txid = module.get('arbitration_id')

                    did_list = []
                    data_identifiers = {}
                    for did_dict in module.get('dids'):
                        did_id = did_dict.get('did_id')
                        did_list.append(did_id)
                        data_identifiers[did_id] = did_dict.get('codec')
                    if len(did_list) == 0:
                        continue
                    self._iso_tp_config['data_identifiers'] = data_identifiers

                    connection = self._module_manager.connection(module_name)
                    if connection is None:
                        no_connection = Response(service=None, code=0x10, data=None)
                        no_connection.valid = False
                        no_connection.invalid_reason = "module has no connection"
                        responses.append({'arbitration_id': txid, 'arbitration_id_hex': f"{txid:04X}", 'did_list': did_list, 'response': no_connection})
                        continue

                    with Client(connection, config=self._iso_tp_config) as client:
                        while len(did_list) > 0:
                            next_read = did_list[0:self._did_read]
                            del did_list[0:self._did_read]
                            try:
                                response = client.read_data_by_identifier(next_read)
                                responses.append({'arbitration_id': txid, 'arbitration_id_hex': f"{txid:04X}", 'response': response})
                            except ValueError as e:
                                _LOGGER.error(f"{txid:04X}: {e}")
                            except ConfigError as e:
                                _LOGGER.error(f"{txid:04X}: {e}")
                            except TimeoutException as e:
                                #_LOGGER.error(f"{txid:04X}: {e}")
                                timeout = Response(service=None, code=0x10, data=None)
                                timeout.valid = False
                                timeout.invalid_reason = "request timed out"
                                responses.append({'arbitration_id': txid, 'arbitration_id_hex': f"{txid:04X}", 'did_list': next_read, 'response': timeout})
                            except NegativeResponseException as e:
                                _LOGGER.error(f"{txid:04X}: {e}")
                            except UnexpectedResponseException as e:
                                _LOGGER.error(f"{txid:04X}: {e}")
                            except InvalidResponseException as e:
                                _LOGGER.error(f"{txid:04X}: {e}")
                            except Exception as e:
                                _LOGGER.error(f"Unexpected exception: {e}")
                try:
                    self.response_queue.put(responses)
                except Full:
                    _LOGGER.error(f"no space in the response queue")
                    return

        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return
