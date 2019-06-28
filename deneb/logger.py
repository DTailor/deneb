"""Logger config for project"""
import logging
import os
from typing import Any

import logzero
import sentry_sdk

from deneb.config import VERSION


def get_logger(name: str) -> Any:
    """Init logger"""
    _formatter = logzero.LogFormatter(
        fmt="%(asctime)-15s %(name)-31s:%(lineno)-3d [%(levelname)s] %(message)s"
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
    kwargs = {}
    environ = os.environ.get("ENVIRON")
    if environ:
        kwargs["environment"] = environ

    server_name = os.environ.get("SERVER_NAME")
    if server_name:
        kwargs["server_name"] = server_name

    if sentry_url:
        sentry_sdk.init(sentry_url, release=VERSION, **kwargs)

    return logger
