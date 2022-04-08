"""Module handling the application and production log files"""

import os
import sys
import logging


_LOG_FILENAME = ""
_LOGGER = logging.getLogger('mme')


def rollover(filename: str) -> None:
    """Rollover the application log."""
    path = os.path.dirname(os.path.abspath(_LOG_FILENAME))
    saved_log = f"{path}/{filename}.log"
    os.rename(_LOG_FILENAME, saved_log)
    _LOGGER.info(f"Created application log {_LOG_FILENAME} after rollover of {filename}")


def start(log_file: str) -> None:
    """Create the application log."""
    global _LOG_FILENAME

    # Disable UDS/ISO-TP library logging
    logging.getLogger().addHandler(logging.NullHandler())

    # Create the directory if needed
    filename = os.path.expanduser(log_file)
    filename_parts = os.path.split(filename)
    if filename_parts[0] and not os.path.isdir(filename_parts[0]):
        os.mkdir(filename_parts[0])
    filename = os.path.abspath(filename)
    _LOG_FILENAME = filename

    # Log to a file
    log_format = '{asctime} {module:16s} {levelname:6s} {message}'
    file_handler = logging.handlers.WatchedFileHandler(filename, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(fmt=log_format, style='{'))

    # Add some console output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(fmt=log_format, style='{'))

    # Create loggers
    logger = logging.getLogger('mme')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # First log entry
    logger.info("Created application log %s", filename)
