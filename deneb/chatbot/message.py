import requests

from deneb.logger import get_logger
from deneb.structs import FBAltert


_LOGGER = get_logger(__name__)


def grouper(size, data):
    """helper to splita data in chunks of size"""
    to_return = ""
    for line in data.splitlines():
        if len(to_return) + len(line) <= size:
            to_return = f"{to_return}{line}\n"
        else:
            yield to_return
            to_return = ""
    yield to_return


def send_message(
        fb_id: str,
        fb_alert: FBAltert,
        data: str,
):
    """send fb user text message"""
    fb_token = {"access_token": fb_alert.key}

    # max message size is 2000
    for msg_chunk in grouper(2000, data):
        clean_chunk = [a for a in msg_chunk if a is not None]
        contents = {
            "recipient": {"id": fb_id},
            "message": {"text": ''.join(clean_chunk)},
        }
        try:
            res = requests.post(fb_alert.url, json=contents, params=fb_token)
            if res.status_code != 200:
                _LOGGER.info(f"{res} {res.content}")
        except Exception as exc:
            _LOGGER.exception(f"failed to send message {exc}")
