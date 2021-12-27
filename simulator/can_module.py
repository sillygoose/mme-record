from pid import PID


class CanModule:
    def __init__(self, name, bus, address) -> None:
        self._name = name
        self._bus= bus
        self._address = address
        self._pids = {}

    def start(self) -> None:
        print(f"Starting CanModule {self._name}")

    def stop(self) -> None:
        print(f"Stopping CanModule {self._name}")

    def addPID(self, pid) -> None:
        pid = PID()

    def name(self) -> str:
        return self._name

    def bus(self) -> str:
        return self._bus

    def address(self) -> int:
        return self._address
