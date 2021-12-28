import time
from becm import BECM

from sobdm import SOBDM
from apim import APIM
from ipc import IPC
from pcm import PCM
from gwm import GWM
from dcdc import DCDC
from bcm import BCM
from becm import BECM


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
        SOBDM(), APIM(), IPC(), PCM(), GWM(), DCDC(), BCM(), BECM(),
    ]

    mme = MustangMachE()
    mme.addModules(modules)
    mme.start()
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    mme.stop()


if __name__ == '__main__':
    main()
