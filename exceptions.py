"""Exceptions used in mme-sim."""

from enum import Enum, auto


class NormalCompletion(Exception):
    """Normal completion, no errors."""


class AbnormalCompletion(Exception):
    """Abnormal completion, error or exception detected."""


class FailedInitialization(Exception):
    """mme-sim initialization failed."""


class TerminateSignal(Exception):
    """SIGTERM."""
