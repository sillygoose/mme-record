import sys
import logging
from queue import Queue
#from typing import List

import version
import logfiles
from readconfig import read_config

from rec_modmgr import RecordModuleManager
from rec_canmgr import RecordCanbusManager
from exceptions import FailedInitialization, RuntimeError


_LOGGER = logging.getLogger('mme')


class Record:
    def __init__(self, config: dict) -> None:
        self._config = dict(config.mme.record)
        self._module_manager = RecordModuleManager(config=self._config)
        self._input_queue = Queue(maxsize=10)
        self._output_queue = Queue(maxsize=10)
        self._canbus_manager = RecordCanbusManager(config=self._config, input_jobs=self._input_queue, output_jobs=self._output_queue)

    def start(self) -> None:
        self._module_manager.start()
        self._canbus_manager.start()

    def stop(self) -> None:
        self._canbus_manager.stop()
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
