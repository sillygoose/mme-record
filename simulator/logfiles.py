"""Module handling the application and production log files"""

import os
import sys
import logging


def start():
    """Create the application log."""
    _DEFAULT_LOG_FILE = 'log/mme.log'
    _DEFAULT_LOG_FORMAT = '[%(asctime)s] [%(module)s] [%(levelname)s] %(message)s'
    _DEFAULT_LOG_LEVEL = logging.INFO

    # Disable UDS/ISO-TP library logging
    logging.getLogger().addHandler(logging.NullHandler())

    _DEBUG_ENV_VAR = 'MME_DEBUG'
    debug_mode = os.getenv(_DEBUG_ENV_VAR, 'False').lower() in ('true', '1', 't')

    log_file = _DEFAULT_LOG_FILE
    log_format = _DEFAULT_LOG_FORMAT
    log_level = _DEFAULT_LOG_LEVEL if not debug_mode else logging.DEBUG

    # Create the directory if needed
    filename = os.path.expanduser(log_file)
    filename_parts = os.path.split(filename)
    if filename_parts[0] and not os.path.isdir(filename_parts[0]):
        os.mkdir(filename_parts[0])
    filename = os.path.abspath(filename)

    # Log to a file
    file_handler = logging.FileHandler(filename, mode='w', encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(fmt=log_format))

    # Add some console output 
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(fmt=log_format))

    # Create loggers
    logger = logging.getLogger('mme')
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # First log entry
    logger.info("Created application log %s", filename)
