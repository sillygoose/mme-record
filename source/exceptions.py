"""Exceptions used in Playback and Record."""
import signal
import logging


_LOGGER = logging.getLogger('mme')


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


class SigTermCatcher:

    _callback_functions = []

    def __init__(self, callback):
        if len(SigTermCatcher._callback_functions) == 0:
            signal.signal(signal.SIGINT, self._sigterm_caught)
            signal.signal(signal.SIGTERM, self._sigterm_caught)
        SigTermCatcher._callback_functions.append(callback)

    def _sigterm_caught(self, *args):
        _LOGGER.info(f"Received SIGTERM signal, shutting down")
        for callback in SigTermCatcher._callback_functions:
            callback()
