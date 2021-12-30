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
        self._pids_by_module = {}

    def start(self) -> None:
        for module in self._modules.values():
            module.start()

    def stop(self) -> None:
        for module in self._modules.values():
            module.stop()

    def addModules(self) -> None:
        config = self._config.modules
        if len(config) == 0:
            raise FailedInitialization("Must define at least one module in the YAML file")

        for yaml_module in config:
            module = yaml_module.get('module', None)
            if module is None:
                raise FailedInitialization("Error parsing module definition in the YAML file")
            name = module.get('name', None)
            channel = module.get('channel', None)
            arbitration_id = module.get('arbitration_id', None)
            self._modules[name] = Module(name=name, channel=channel, arbitration_id=arbitration_id)

    def addPIDs(self) -> None:
        config = self._config.pids
        if len(config) == 0:
            raise FailedInitialization("Must define at least one PID in the YAML file")

        for yaml_pid in config:
            pid = yaml_pid.get('pid', None)
            if pid is None:
                raise FailedInitialization("Error parsing PID definition in the YAML file")
            name = pid.get('name', None)
            id = pid.get('id', None)
            packing = pid.get('packing', None)
            states = pid.get('states', None)
            pid_object = PID(id=id, name=name, packing=packing, states=states)
            self._pids_by_id[id] = pid_object

            pid_modules = pid.get('modules', None)
            for module_name in pid_modules:
                name = module_name.get('module')
                module_object = self._modules.get(name, None)
                if module_object is not None:
                    module_object.addPID(pid_object)


#if self._pids_by_module[id]
            #self._pids_by_module[id] = pid_object




def main() -> None:
    """
    modules = [
        APIM(), #SOBDM(), IPC(), PCM(), GWM(), DCDC(), BCM(), BECM(),
    ]
    """
    
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
        mme.addModules()
        mme.addPIDs()
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
