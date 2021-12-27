
#pids = [
#    { 'SOBDM', []}
#]

class PID:
    def __init__(self, id, name) -> None:
        self._id = id
        self._name = name
        self._enable = False

    def start(self) -> None:
        print(f"Starting PID {self._name}")
        self._enable= True

    def stop(self) -> None:
        print(f"Stopping PID {self._name}")
        self._enable = False

    def name(self) -> str:
        return self._name

    def id(self) -> int:
        return self._id
