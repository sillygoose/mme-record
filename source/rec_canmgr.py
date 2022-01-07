import threading
import logging
from time import sleep, time
from queue import Empty, Full, Queue
#from typing import List

import udsoncan.configs
from udsoncan.client import Client
from udsoncan.exceptions import *

import rec_codecs
from rec_modmgr import RecordModuleManager

#from exceptions import FailedInitialization, RuntimeError


_LOGGER = logging.getLogger('mme')


class RecordCanbusManager:
    mach_e = [
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x411F, 'codec': rec_codecs.CodecKeyState},            # Ignition state
            ]},
        {'module': 'APIM', 'address': 0x7D0, 'bus': 'can1', 'dids': [
                {'did': 0x8012, 'codec': rec_codecs.CodecGPS},                 # GPS data
            ]},
    ]

    def __init__(self, config: dict, input_jobs: Queue, output_jobs: Queue) -> None:
        self._config = config
        self._input_jobs = input_jobs
        self._output_jobs = output_jobs
        self._exit_requested = False
        self._timeout = 2.0
        self._iso_tp_config = dict(udsoncan.configs.default_client_config)
        self._iso_tp_config['request_timeout'] = self._timeout
        self._iso_tp_config['p2_timeout'] = self._timeout
        self._iso_tp_config['p2_star_timeout'] = self._timeout
        self._iso_tp_config['logger_name'] = 'mme'

    def start(self) -> None:
        self._exit_requested = False
        self._thread = threading.Thread(target=self._work_task, name='record')
        self._thread.start()
        while True:
            sleep(1)
            try:
                #_LOGGER.info(f"input job queue is {self._input_jobs.empty()}")
                self._input_jobs.put(RecordCanbusManager.mach_e, block=True, timeout=1)
            except Full:
                _LOGGER.error(f"no space in the work queue")
                self._exit_requested = True
            try:
                #_LOGGER.info(f"input job queue is {self._input_jobs.empty()}")
                work_product = self._output_jobs.get(block=True)
                print(work_product.get('decoded'))
            except Full:
                _LOGGER.error(f"no space in the work queue")
                self._exit_requested = True
        self._thread.join() ###

    def stop(self) -> None:
        self._exit_requested = True
        if self._thread.is_alive():
            self._thread.join()

    def _work_task(self) -> None:
        try:
            while self._exit_requested == False:
                try:
                    #_LOGGER.info(f"input job queue empty is {self._input_jobs.empty()}")
                    job = self._input_jobs.get(block=True, timeout=5)
                    #_LOGGER.info(f"input job queue empty is {self._input_jobs.empty()}")
                except Empty:
                    continue

                for module in job:
                    module_name = module.get('module')
                    txid = module.get('address')
                    conn = RecordModuleManager.connection(module_name)

                    did_list = []
                    data_identifiers = {}
                    for did_dict in module.get('dids'):
                        did = did_dict.get('did')
                        did_list.append(did)
                        data_identifiers[did] = did_dict.get('codec')
                    if len(did_list) == 0:
                        continue
                    self._iso_tp_config['data_identifiers'] = data_identifiers

                    with Client(conn, request_timeout=self._timeout, config=self._iso_tp_config) as client:
                        try:
                            response = client.read_data_by_identifier(did_list)
                            for did in did_list:
                                payload = response.service_data.values[did].get('payload')
                                decoded = response.service_data.values[did].get('decoded')
                                key = f"{txid:04X} {did:04X}"
                                #print(decoded)
                                self._output_jobs.put(response.service_data.values[did])

                        except ValueError as e:
                            _LOGGER.error(f"{txid:04X}: {e}")
                        except ConfigError as e:
                            _LOGGER.error(f"{txid:04X}: {e}")
                        except TimeoutException as e:
                            _LOGGER.error(f"{txid:04X}: {e}")
                        except NegativeResponseException as e:
                            _LOGGER.error(f"{txid:04X}: {e}")
                        except UnexpectedResponseException as e:
                            _LOGGER.error(f"{txid:04X}: {e}")
                        except InvalidResponseException as e:
                            _LOGGER.error(f"{txid:04X}: {e}")
                        except Exception as e:
                            _LOGGER.error(f"Unexpected excpetion: {e}")
        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return
