import sys
import os
import time
import logging
from typing import List

from module import Module, builtin_modules
from pid import _PIDS, PID, builtin_pids

import version
import logfiles
from readconfig import read_config

from exceptions import FailedInitialization


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

    def add_custom_modules(self, modules: dict) -> None:
        if len(modules) == 0:
            raise FailedInitialization("Must define at least one module in YAML file")

        for module in modules:
            module_settings = module.get('module', None)
            if module_settings is None:
                raise FailedInitialization("Error parsing custom module definition in YAML file")
            name = module_settings.get('name', None)
            channel = module_settings.get('channel', None)
            arbitration_id = module_settings.get('arbitration_id', None)
            self._modules[name] = Module(name=name, channel=channel,arbitration_id=arbitration_id)

    def add_custom_pids(self, pids: dict) -> None:
        if len(pids) == 0:
            raise FailedInitialization("Must define at least one PID in YAML file")

        for pid_item in pids:
            pid = pid_item.get('pid', None)
            if pid is None:
                raise FailedInitialization("Error parsing custom PID definition in YAML file")

            id = pid.get('id', None)
            name = pid.get('name', None)
            packing = pid.get('packing', None)
            modules = pid.get('modules', None)
            states = pid.get('states', None)

            if self._pids_by_id.get(id, None) is not None:
                raise FailedInitialization(f"PID {pid:04X} is defined more than once in the YAML file")
            pid_object = PID(id=id, name=name, packing=packing, modules=modules, states=states)
            self._pids_by_id[id] = pid_object
            _LOGGER.info(f"Added PID {id:04X} to simulator")

            pid_modules = pid_object.used_in()
            for module_name in pid_modules:
                module_object = self._modules.get(module_name, None)
                if module_object is not None:
                    module_object.add_pid(pid_object)

    def add_builtin_modules(self, modules: List[str]) -> None:
        for module in modules:
            if self._modules.get(module, None) is not None:
                raise FailedInitialization(f"Module {module} is defined more than once")
            self._modules[module] = Module(name=module)
            _LOGGER.debug(f"Added module '{module}' to simulator")

    def add_builtin_pids(self, pids: List[int]) -> None:
        for pid in pids:
            if self._pids_by_id.get(pid, None) is not None:
                raise FailedInitialization(f"PID {pid:04X} is defined more than once in the YAML file")
            pid_object = PID(id=pid)
            self._pids_by_id[pid] = pid_object
            _LOGGER.debug(f"Added PID {pid:04X} to simulator")

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
        builtin = config.mme.builtin
        if builtin.modules == True:
            mme.add_builtin_modules(builtin_modules())
        if 'custom' in config.mme.keys():
            custom = config.mme.custom
            if 'modules' in custom.keys():
                mme.add_custom_modules(custom.modules)

        if builtin.pids == True:
            mme.add_builtin_pids(builtin_pids())
        if 'custom' in config.mme.keys():
            custom = config.mme.custom
            if 'pids' in custom.keys():
                mme.add_custom_pids(custom.pids)
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
