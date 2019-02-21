"""Logger config for project"""
import logging
import os
from typing import Any

import logzero
import sentry_sdk


def get_logger(name: str) -> Any:
    """Init logger"""
    _formatter = logzero.LogFormatter(
        fmt="%(asctime)-15s %(name)s:%(lineno)d [%(levelname)s] %(message)s"
    )
    logger = logzero.setup_logger(
        name=name,
        logfile="logfile.log",
        level=logging.DEBUG,
        formatter=_formatter,
        maxBytes=1e6,
        backupCount=5,
    )

    sentry_url = os.environ.get("SENTRY_URL")
    if sentry_url:
        sentry_sdk.init(sentry_url)

    return logger
