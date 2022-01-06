"""Exceptions used in the simulator."""

class NormalCompletion(Exception):
    """Normal completion, no errors."""


class AbnormalCompletion(Exception):
    """Abnormal completion, error or exception detected."""


class FailedInitialization(Exception):
    """Record/Playback initialization failed."""


class RuntimeError(Exception):
    """Record/Playback run-time error."""


class TerminateSignal(Exception):
    """SIGTERM."""
