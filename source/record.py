import sys
import os
from queue import Queue
import logging
from typing import List

#import module
#from module import Module

#import did
#from did import DID
#from rcengine import RecordEngine

import version
import logfiles
from readconfig import read_config

from exceptions import FailedInitialization, RuntimeError


_LOGGER = logging.getLogger('mme')


class Record:
    def __init__(self, config: dict) -> None:
        self._config = dict(config.mme.record)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def event_queues(self) -> dict:
        return None


def main() -> None:

    logfiles.start()
    _LOGGER.info(f"Mustang Mach E Record Utility version {version.get_version()}")

    try:
        config = read_config(yaml_file='mme.yaml')
        if config is None:
            return
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.error(f"Unexpected exception: {e}")
        return

    try:
        mme = Record(config=config)
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.error(f"Unexpected exception setting up Record: {e}")
        return

    try:
        mme.start()
    except KeyboardInterrupt:
        pass
    except RuntimeError:
        pass
    except Exception as e:
        _LOGGER.error(f"Unexpected exception: {e}")
    finally:
        mme.stop()


if __name__ == '__main__':
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
        main()
    else:
        print("python 3.10 or better required")
