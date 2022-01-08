import sys
import logging
from queue import Queue
#from typing import List

import version
import logfiles
from readconfig import read_config

from rec_modmgr import RecordModuleManager
from rec_canmgr import RecordCanbusManager
from rec_statemgr import RecordStateManager
from exceptions import FailedInitialization, RuntimeError


_LOGGER = logging.getLogger('mme')


class Record:
    def __init__(self, config: dict) -> None:
        self._config = dict(config.mme.record)
        self._module_manager = RecordModuleManager(config=self._config)
        self._request_queue = Queue(maxsize=10)
        self._response_queue = Queue(maxsize=10)
        self._canbus_manager = RecordCanbusManager(config=self._config, request_queue=self._request_queue, response_queue=self._response_queue)
        self._state_manager = RecordStateManager(config=self._config, request_queue=self._request_queue, response_queue=self._response_queue)

    def start(self) -> None:
        self._module_manager.start()
        threads = []
        threads.append(self._state_manager.start())
        threads.append(self._canbus_manager.start())
        for thread_list in threads:
            for thread in thread_list:
                thread.join()

    def stop(self) -> None:
        self._canbus_manager.stop()
        self._state_manager.start()
        self._module_manager.stop()



def main() -> None:

    logfiles.start('log/record.log')
    _LOGGER.info(f"Mustang Mach E Record Utility version {version.get_version()}")

    try:
        config = read_config(yaml_file='mme.yaml')
        if config is None:
            return
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.exception(f"Unexpected exception: {e}")
        return

    try:
        recorder = Record(config=config)
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.exception(f"Unexpected exception setting up Record: {e}")
        return

    try:
        recorder.start()
    except KeyboardInterrupt:
        print()
    except RuntimeError as e:
        _LOGGER.exception(f"Run time error: {e}")
    except Exception as e:
        _LOGGER.exception(f"Unexpected exception: {e}")
    finally:
        recorder.stop()


if __name__ == '__main__':
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
        main()
    else:
        print("python 3.10 or better required")
