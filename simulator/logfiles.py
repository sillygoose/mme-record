"""Module handling the application and production log files"""

import os
import sys
import logging


_LOGGER = logging.getLogger()

_DEFAULT_LOG_FILE = 'log/mme'
_DEFAULT_LOG_FORMAT = '[%(asctime)s] [%(module)s] [%(levelname)s] %(message)s'
_DEFAULT_LOG_LEVEL = 'WARNING'


def start():
    """Create the application log."""

    _DEBUG_ENV_VAR = 'MME_DEBUG'
    debug_mode = os.getenv(_DEBUG_ENV_VAR, 'False').lower() in ('true', '1', 't')

    log_file = _DEFAULT_LOG_FILE
    log_format = _DEFAULT_LOG_FORMAT
    log_level = _DEFAULT_LOG_LEVEL if not debug_mode else 'DEBUG'

    # Create the directory if needed
    filename = os.path.expanduser(log_file + ".log")
    filename_parts = os.path.split(filename)
    if filename_parts[0] and not os.path.isdir(filename_parts[0]):
        os.mkdir(filename_parts[0])
    filename = os.path.abspath(filename)

    #logging.basicConfig(filename=filename, level=log_level, format=log_format)

    # Log to a file
    handler = logging.FileHandler(filename, encoding='utf-8')
    handler.setLevel(log_level)
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    _LOGGER.addHandler(handler)

    # Add some console output 
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    _LOGGER.addHandler(console_handler)
    _LOGGER.setLevel(log_level)

    # First entry
    _LOGGER.info("Created application log %s", filename)
