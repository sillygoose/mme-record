"""Exceptions used in the simulator."""

class NormalCompletion(Exception):
    """Normal completion, no errors."""


class AbnormalCompletion(Exception):
    """Abnormal completion, error or exception detected."""


class FailedInitialization(Exception):
    """Simulator initialization failed."""


class TerminateSignal(Exception):
    """SIGTERM."""
