"""Logger config for project"""
import logging
import os
from typing import Any, Dict, Optional, Union  # noqa

import logzero
import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from deneb.config import VERSION


def push_sentry_error(
    exc: Union[Exception, str],
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    is_exc: bool = True,
) -> None:
    user = {
        "id": user_id,
        "name": username,
    }

    with sentry_sdk.push_scope() as scope:
        scope.user = user
        if is_exc:
            sentry_sdk.capture_exception(exc)
        else:
            sentry_sdk.capture_message(exc)


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
    sentry_kwargs = {}  # type: Dict[str, Any]

    sentry_kwargs["integrations"] = [
        AioHttpIntegration(),
        SqlalchemyIntegration(),
        CeleryIntegration(),
    ]
    environ = os.environ.get("ENVIRON")
    if environ:
        sentry_kwargs["environment"] = environ

    server_name = os.environ.get("SERVER_NAME")
    if server_name:
        sentry_kwargs["server_name"] = server_name

    if sentry_url:
        sentry_sdk.init(sentry_url, release=VERSION, **sentry_kwargs)

    return logger
