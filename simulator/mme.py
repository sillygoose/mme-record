import sys
import os
import time
import logging

from module import Module
from pid import PID

import version
import logfiles
from readconfig import read_config

from exceptions import FailedInitialization

"""
from apim import APIM
from sobdm import SOBDM
from ipc import IPC
from pcm import PCM
from gwm import GWM
from dcdc import DCDC
from bcm import BCM
from becm import BECM
"""


_LOGGER = logging.getLogger('mme')


class MustangMachE:
    def __init__(self, config: dict) -> None:
        self._modules = {}
        self._config = config.mme
        self._modules = {}
        self._pids_by_id = {}

    def start(self) -> None:
        for module in self._modules.values():
            module.start()

    def stop(self) -> None:
        for module in self._modules.values():
            module.stop()

    def add_modules_from_yaml(self) -> None:
        config = self._config.modules
        if len(config) == 0:
            raise FailedInitialization("Must define at least one module in YAML file")

        for yaml_module in config:
            module_name = yaml_module.get('module', None)
            if module_name is None:
                raise FailedInitialization("Error parsing module definition in YAML file")
            self._modules[module_name] = Module(name=module_name)

    def add_pids_from_yaml(self) -> None:
        config = self._config.pids
        if len(config) == 0:
            raise FailedInitialization("Must define at least one PID in YAML file")

        for yaml_pid in config:
            pid = yaml_pid.get('pid', None)
            if pid is None:
                raise FailedInitialization("Error parsing PID definition in YAML file")
            if self._pids_by_id.get(pid, None) is not None:
                raise FailedInitialization(f"PID {pid:04X} is defined more than once in the YAML file")
            pid_object = PID(id=pid)
            self._pids_by_id[pid] = pid_object
            _LOGGER.info(f"Added PID {pid:04X} to simulator")

            pid_modules = pid_object.used_in()
            for module_name in pid_modules:
                module_object = self._modules.get(module_name, None)
                if module_object is not None:
                    module_object.add_pid(pid_object)


def main() -> None:

    logfiles.start()
    _LOGGER.info(f"MME Simulator version {version.get_version()}, PID is {os.getpid()}")

    try:
        config = read_config()
        if config is None:
            return
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.error(f"Unexpected exception: {e}")
        return

    try:
        mme = MustangMachE(config=config)
        mme.add_modules_from_yaml()
        mme.add_pids_from_yaml()
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.error(f"Unexpected exception: {e}")
        return

    try:
        mme.start()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break
    except FailedInitialization as e:
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
