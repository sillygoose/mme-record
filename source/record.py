import sys
import logging
from queue import Queue
#from typing import List

import version
import logfiles
from readconfig import read_config

from rec_modmgr import RecordModuleManager
from rec_engine import RecordEngine
from exceptions import FailedInitialization, RuntimeError


_LOGGER = logging.getLogger('mme')


class Record:
    def __init__(self, config: dict) -> None:
        self._config = dict(config.mme.record)
        self._module_manager = RecordModuleManager(config=self._config)
        self._work_queue = Queue(maxsize=10)
        self._record_engine = RecordEngine(config=self._config, work_queue=self._work_queue)

    def start(self) -> None:
        self._module_manager.start()
        self._record_engine.start()

    def stop(self) -> None:
        self._record_engine.stop()
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
