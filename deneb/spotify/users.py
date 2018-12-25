"""Entry point to deneb spotify watcher"""

from typing import Optional

from deneb.artist_update import get_new_releases
from deneb.db import User
from deneb.logger import get_logger
from deneb.sp import spotify_client
from deneb.structs import SpotifyKeys
from deneb.user_update import fetch_user_followed_artists

_LOGGER = get_logger(__name__)


def update_users_artists(
    credentials: SpotifyKeys, user_id: Optional[str] = None, force_update: bool = False
):
    users = User.select()

    if user_id:
        users = [User.get(User.username == user_id)]

    for user in users:
        if not user.spotify_token:
            _LOGGER.info(f"can't update {user}, has no token yet.")
            continue

        _LOGGER.info(f"updating {user} ...")

        with spotify_client(credentials, user) as sp:  # type: ignore
            new_follows, lost_follows = fetch_user_followed_artists(user, sp)

            new_follows_str = ", ".join(str(a) for a in new_follows)
            lost_follows_str = ", ".join(str(a) for a in lost_follows)

            _LOGGER.info(
                f"new follows for {user} ({len(new_follows)}): {new_follows_str}"
            )
            _LOGGER.info(
                f"lost follows for {user} ({len(lost_follows)}): {lost_follows_str}"
            )

            _LOGGER.info("now updating user artists")
            albums_nr, updated_nr = get_new_releases(sp, user.following, force_update)
            _LOGGER.info(f"fetched {albums_nr} albums for {updated_nr} artists")
