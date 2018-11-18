"""Entry point to deneb spotify watcher"""

from artist_update import get_new_releases
from db import get_or_create_user
from logger import get_logger
from sp import get_sp_client
from user_update import fetch_user_followed_artists

_LOGGER = get_logger(__name__)


def main(username, fb_id):
    _LOGGER.info('')
    _LOGGER.info('------------ RUN UPDATE ARTISTS ---------------')
    _LOGGER.info('')
    sp, token = get_sp_client(username)
    user, created = get_or_create_user(fb_id)
    user.update_market(sp.client.current_user())
    _LOGGER.info(f"Using {user}; created status is {created}")

    new_follows, lost_follows = fetch_user_followed_artists(user, sp)

    new_follows_str = ", ".join(str(a) for a in new_follows)
    _LOGGER.info(f"new follows for {user} ({len(new_follows)}): {new_follows_str}")

    lost_follows_str = ", ".join(str(a) for a in lost_follows)
    _LOGGER.info(f"lost follows for {user} ({len(lost_follows)}): {lost_follows_str}")

    try:
        get_new_releases(sp)
    except Exception as exc:
        _LOGGER.exception(f"{sp} client failed. exc: {exc}")
        raise


main('dann.croitoru', 'dann.croitoru1111')
