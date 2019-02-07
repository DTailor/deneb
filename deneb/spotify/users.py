"""Entry point to deneb spotify watcher"""

from typing import Optional

from deneb.artist_update import get_new_releases
from deneb.db import User
from deneb.logger import get_logger
from deneb.sp import spotify_client
from deneb.structs import SpotifyKeys
from deneb.user_update import fetch_user_followed_artists

_LOGGER = get_logger(__name__)


async def update_users_artists(
    credentials: SpotifyKeys, user_id: Optional[str] = None, force_update: bool = False
):
    if user_id:
        users = await User.filter(username=user_id)
    else:
        users = await User.all()

    for user in users:
        if not user.spotify_token:
            _LOGGER.info(f"can't update {user}, has no token yet.")
            continue

        _LOGGER.info(f"updating {user} ...")

        async with spotify_client(credentials, user) as sp:
            new_follows, lost_follows = await fetch_user_followed_artists(user, sp)

            new_follows_str = ", ".join(str(a) for a in new_follows)
            lost_follows_str = ", ".join(str(a) for a in lost_follows)

            _LOGGER.info(
                f"new follows for {user} ({len(new_follows)}): {new_follows_str}"
            )
            _LOGGER.info(
                f"lost follows for {user} ({len(lost_follows)}): {lost_follows_str}"
            )

            _LOGGER.info("now updating user artists")
            followed_artists = await user.artists.filter()
            albums_nr, updated_nr = await get_new_releases(
                sp, followed_artists, force_update
            )
            _LOGGER.info(f"fetched {albums_nr} albums for {updated_nr} artists")
