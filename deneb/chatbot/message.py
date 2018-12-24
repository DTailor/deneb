import requests

from deneb.logger import get_logger
from deneb.structs import FBAltert

_LOGGER = get_logger(__name__)


def send_message(
        fb_id: str,
        fb_alert: FBAltert,
        data: str,
):
    """send fb user text message"""

    fb_token = {"access_token": fb_alert.key}
    contents = {
        "recipient": {"id": fb_id},
        "message": {"text": data},
    }
    try:
        res = requests.post(fb_alert.url, json=contents, params=fb_token)
        if res.status_code != 200:
            _LOGGER.info(f"{res} {res.content}")
    except Exception as exc:
        _LOGGER.exception(f"failed to send message {exc}")
