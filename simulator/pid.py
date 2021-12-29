
class PID:
    def __init__(self, id: int, name: str) -> None:
        self._id = id
        self._name = name

    def name(self) -> str:
        return self._name

    def id(self) -> int:
        return self._id
