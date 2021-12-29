import sys
import os
import time
import logging

import version
import logfiles
from readconfig import read_config

from exceptions import FailedInitialization

from apim import APIM
from sobdm import SOBDM
from ipc import IPC
from pcm import PCM
from gwm import GWM
from dcdc import DCDC
from bcm import BCM
from becm import BECM


_LOGGER = logging.getLogger('mme')


class MustangMachE:
    def __init__(self, vin=None) -> None:
        self.modules = {}
        self.vin = vin

    def start(self) -> None:
        for module in self.modules.values():
            module.start()

    def stop(self) -> None:
        for module in self.modules.values():
            module.stop()

    def addModule(self, module) -> None:
        self.modules[module.name()] = module

    def addModules(self, modules) -> None:
        for module in modules:
            self.modules[module.name()] = module




def main():
    modules = [
        APIM(), # SOBDM(), IPC(), PCM(), GWM(), DCDC(), BCM(), BECM(),
    ]

    logfiles.start()
    _LOGGER.info(f"MME Simulator version {version.get_version()}, PID is {os.getpid()}")

    try:
        config = read_config()
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.error(f"Unexpected exception: {e}")
        return

    try:
        mme = MustangMachE()
        mme.addModules(modules)
        mme.start()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break
    except Exception as e:
        _LOGGER.error(f"Unexpected exception: {e}")
    finally:
        mme.stop()


if __name__ == '__main__':
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
        main()
    else:
        print("python 3.10 or better required")
