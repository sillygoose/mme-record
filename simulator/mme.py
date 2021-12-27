from can_module import CanModule


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


modules = [
    CanModule('SOBDM', 'can0', 0x7E2),
    CanModule('BECM', 'can0', 0x7E4),
    CanModule('APIM', 'can1', 0x7D0),
]


def main():
    mme = MustangMachE()

    mme.addModules(modules)
    #mme.addModule(CanModule('APIM', 'can1', 0x7D0))
    
    mme.start()
    
    mme.stop()


if __name__ == '__main__':
    main()
