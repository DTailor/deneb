"""Entry point to deneb spotify watcher"""

from artist_update import get_new_releases
from db import User
from logger import get_logger
from sp import get_sp_client
from user_update import fetch_user_followed_artists

_LOGGER = get_logger(__name__)


def update_users_follows():
    _LOGGER.info('')
    _LOGGER.info('------------ RUN UPDATE ARTISTS ---------------')
    _LOGGER.info('')
    for user in User.select():
        _LOGGER.info(f"Updating {user} ...")
        sp, _ = get_sp_client(user.username, user.spotify_token)
        user.update_market(sp.client.current_user())

        new_follows, lost_follows = fetch_user_followed_artists(user, sp)

        new_follows_str = ", ".join(str(a) for a in new_follows)

        lost_follows_str = ", ".join(str(a) for a in lost_follows)
        _LOGGER.info(f"new  follows for {user} ({len(new_follows)}): {new_follows_str}")
        _LOGGER.info(f"lost follows for {user} ({len(lost_follows)}): {lost_follows_str}")

        try:
            albums_nr, updated_nr = get_new_releases(sp)
            _LOGGER.info(f"fetched {albums_nr} albums for {updated_nr} artists")
        except Exception as exc:
            _LOGGER.exception(f"{sp} client failed. exc: {exc}")
            raise


update_users_follows()
