"""Entry point to deneb spotify watcher"""

from typing import Optional

from deneb.artist_update import get_new_releases
from deneb.config import Config
from deneb.db import User
from deneb.logger import get_logger
from deneb.sp import spotify_client
from deneb.structs import SpotifyKeys
from deneb.tools import run_tasks
from deneb.user_update import fetch_user_followed_artists

_LOGGER = get_logger(__name__)


async def _update_user_artists(
    credentials: SpotifyKeys, user: User, force_update: bool
):
    async with spotify_client(credentials, user) as sp:
        new_follows, lost_follows = await fetch_user_followed_artists(user, sp)

        new_follows_str = ", ".join(str(a) for a in new_follows)
        lost_follows_str = ", ".join(str(a) for a in lost_follows)

        followed_artists = await user.artists.filter()

        _LOGGER.info(
            f"new follows for {user} ({len(new_follows)}): {new_follows_str}"
            f"lost follows for {user} ({len(lost_follows)}): {lost_follows_str}"
            f"now updating {user} artists ({len(followed_artists)})"
        )  # flake8: noqa
        albums_nr, updated_nr = await get_new_releases(
            sp, followed_artists, force_update
        )
        _LOGGER.info(f"fetched {albums_nr} albums for {updated_nr} artists")


def _user_task_filter(args):
    if args[1].spotify_token:
        return True
    return False


async def update_users_artists(
    credentials: SpotifyKeys, user_id: Optional[str] = None, force_update: bool = False
):
    if user_id:
        users = await User.filter(username=user_id)
    else:
        users = await User.all()

    args_items = [(credentials, user, force_update) for user in users]
    await run_tasks(
        Config.USERS_TASKS_AMOUNT, args_items, _update_user_artists, _user_task_filter
    )
