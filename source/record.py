import sys
import os
import logging
from queue import Queue
import json

import version
import logfiles
from geocoding import initialize_geocodio

from readconfig import parse_yaml_file, parse_command_line
from config.configuration import Configuration

from did_manager import DIDManager

from record_modmgr import RecordModuleManager
from record_canmgr import RecordCanbusManager
from record_statemgr import RecordStateManager

from exceptions import SigTermCatcher, FailedInitialization, RuntimeError, TerminateSignal


_LOGGER = logging.getLogger('mme')


class Record:
    def __init__(self, config: Configuration) -> None:
        self._request_queue = Queue(maxsize=10)
        self._response_queue = Queue(maxsize=10)
        self._module_manager = RecordModuleManager(config=config)
        self._did_manager = DIDManager()
        initialize_geocodio(config)
        self._canbus_manager = RecordCanbusManager(config=config, request_queue=self._request_queue, response_queue=self._response_queue, module_manager=self._module_manager)
        self._state_manager = RecordStateManager(config=config, request_queue=self._request_queue, response_queue=self._response_queue)

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
        self._state_manager.stop()
        self._module_manager.stop()

    def _load_json(self, file: str) -> None:
        with open(file) as infile:
            try:
                self._current_playback = json.load(infile)
                _LOGGER.info(f"Loaded playback file '{file}'")
            except FileNotFoundError as e:
                raise RuntimeError(f"{e}")
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON error in '{file}' at line {e.lineno}")


def _sigterm() -> None:
    raise TerminateSignal


def main() -> None:
    try:
        yaml_file, log_file = parse_command_line(default_yaml='mme.yaml', default_log='record.log')
        logfiles.start(log_file)
        _LOGGER.info(f"Mustang Mach E Record Utility version {version.get_version()}, PID is {os.getpid()}")

        if config := parse_yaml_file(yaml_file=yaml_file):
            SigTermCatcher(_sigterm)
            record = Record(config=config.mme)
            try:
                record.start()
            except KeyboardInterrupt:
                print()
            except TerminateSignal:
                pass
            finally:
                record.stop()

    except KeyboardInterrupt:
        print()
    except TerminateSignal:
        return
    except RuntimeError as e:
        _LOGGER.error(f"Run time error: {e}")
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
    except Exception as e:
        _LOGGER.exception(f"Unexpected exception: {e}")


if __name__ == '__main__':
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
        main()
    else:
        print("python 3.10 or better required")
