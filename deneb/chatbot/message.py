import requests
from deneb.logger import get_logger

_LOGGER = get_logger(__name__)


def send_message(
        fb_id: str,
        url: str,
        key: str,
        data: str,
):
    """send fb user text message"""
    contents = {
        "fb_id": fb_id,
        "key": key,
        "text": data
    }
    try:
        requests.post(url, json=contents)
    except Exception as exc:
        _LOGGER(f"failed to send message {exc}")
