"""Entry point to deneb spotify watcher"""

import json

from dotenv import load_dotenv

from deneb.artist_update import get_new_releases
from deneb.db import User
from deneb.logger import get_logger
from deneb.sp import get_client
from deneb.user_update import fetch_user_followed_artists

load_dotenv()

_LOGGER = get_logger(__name__)


def update_users_follows(client_id, client_secret, client_redirect_uri):

    for user in User.select():
        if not user.spotify_token:
            _LOGGER.info(f"Can't update {user}, has no token yet.")
            continue

        _LOGGER.info(f"Updating {user} ...")

        token_info = json.loads(user.spotify_token)

        sp = get_client(client_id, client_secret, client_redirect_uri, token_info)
        user.sync_data(sp)

        new_follows, lost_follows = fetch_user_followed_artists(user, sp)

        new_follows_str = ", ".join(str(a) for a in new_follows)

        lost_follows_str = ", ".join(str(a) for a in lost_follows)
        _LOGGER.info(f"new  follows for {user} ({len(new_follows)}): {new_follows_str}")
        _LOGGER.info(
            f"lost follows for {user} ({len(lost_follows)}): {lost_follows_str}"
        )

        try:
            albums_nr, updated_nr = get_new_releases(sp)
            _LOGGER.info(f"fetched {albums_nr} albums for {updated_nr} artists")
        except Exception as exc:
            _LOGGER.exception(f"{sp} client failed. exc: {exc}")
            raise
        finally:
            user.sync_data(sp)
