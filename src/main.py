"""Entry point to deneb spotify watcher"""

from artist_update import get_new_releases
from db import get_or_create_user
from logger import get_logger
from sp import get_sp_client
from user_update import fetch_user_followed_artists

_LOGGER = get_logger(__name__)


def main(username, fb_id):
    _LOGGER.info('')
    _LOGGER.info('------------ RUN ---------------')
    _LOGGER.info('')
    sp, token = get_sp_client(username)
    user, created = get_or_create_user(fb_id)
    user.update_market(sp.client.current_user())
    _LOGGER.info(f"Using {user}; created status is {created}")
    fetch_user_followed_artists(user, sp)
    try:
        get_new_releases(sp)
    except Exception as exc:
        _LOGGER.exception(f"{sp} client failed. exc: {exc}")
        raise


main('dann.croitoru', 'dann.croitoru1111')
