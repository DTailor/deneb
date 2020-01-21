import aiohttp

from deneb.logger import get_logger, push_sentry_error
from deneb.structs import FBAlert

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
    if to_return:
        yield to_return


async def send_message(fb_id: str, fb_alert: FBAlert, data: str):
    """send fb user text message"""
    fb_token = {"access_token": fb_alert.key}

    # max message size is 2000
    async with aiohttp.ClientSession() as session:
        for msg_chunk in grouper(2000, data):
            clean_chunk = [a for a in msg_chunk if a is not None]
            contents = {
                "recipient": {"id": fb_id},
                "message": {"text": "".join(clean_chunk)},
            }
            async with session.post(
                fb_alert.url, json=contents, params=fb_token
            ) as res:
                if res.status != 200:
                    _LOGGER.info(f"{res} {res.content}")
                    try:
                        res.raise_for_status()
                    except aiohttp.ClientError as exc:
                        push_sentry_error(exc, fb_id)
