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
    _sigterm_seen = False

    def __init__(self, callback):
        if len(SigTermCatcher._callback_functions) == 0:
            signal.signal(signal.SIGTERM, self._sigterm_caught)
        SigTermCatcher._callback_functions.append(callback)

    def _sigterm_caught(self, *args):
        if SigTermCatcher._sigterm_seen == False:
            SigTermCatcher._sigterm_seen = True
            _LOGGER.info(f"Received SIGTERM signal, shutting down")
            for callback in SigTermCatcher._callback_functions:
                callback()
            SigTermCatcher._callback_functions.clear()