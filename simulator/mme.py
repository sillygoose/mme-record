from can_module import CanModule


class MustangMachE:
    def __init__(self, vin=None) -> None:
        self.modules = {}
        self.vin = vin

    def start(self) -> None:
        for module in self.modules.values():
            module.start()

    def stop(self) -> None:
        for module in self.modules:
            module.stop()

    def addModule(self, module) -> None:
        self.modules[module.name()] = module


def main():
    mme = MustangMachE()

    mme.addModule(CanModule('APIM', 'can1', 0x7D0))
    
    mme.start()
    
    mme.stop()


if __name__ == '__main__':
    main()
