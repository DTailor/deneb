"""Logger config for project"""
import logging
from typing import Any

import logzero


def get_logger(name: str) -> Any:
    """Init logger"""
    _formatter = logging.Formatter(
        "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
    )
    logger = logzero.setup_logger(
        name=name,
        logfile="logfile.log",
        level=logging.DEBUG,
        formatter=_formatter,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    return logger
