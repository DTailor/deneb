"""Entry point to deneb spotify watcher"""

from typing import List, Optional, Tuple

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
    """task to update user followed artists and artist albums"""
    async with spotify_client(credentials, user) as sp:
        new_follows, lost_follows = await fetch_user_followed_artists(user, sp)

        followed_artists = await user.artists.filter()

        _LOGGER.info(
            f"{user} : follows +{len(new_follows)} -{len(lost_follows)}"
            f"; now updating artists ({len(followed_artists)})"
        )
        albums_nr, updated_nr = await get_new_releases(
            sp, followed_artists, force_update
        )
        if updated_nr:
            _LOGGER.info(f"fetched {albums_nr} albums for {updated_nr} artists")


def _user_task_filter(args: Tuple[SpotifyKeys, User, bool]) -> bool:
    """filter for task runner to check if task should be run"""
    if args[1].spotify_token:
        return True
    return False


async def _get_to_update_users(username: Optional[str] = None) -> List[User]:
    """if `--username` option used, fetch that user else fetch all users"""
    if username:
        users = await User.filter(username=username)
    else:
        users = await User.all()
    return users


async def update_users_artists(
    credentials: SpotifyKeys, user_id: Optional[str] = None, force_update: bool = False
):
    """entry point for updating user artists and artist albums"""
    users = await _get_to_update_users(user_id)
    args_items = [(credentials, user, force_update) for user in users]
    await run_tasks(
        Config.USERS_TASKS_AMOUNT, args_items, _update_user_artists, _user_task_filter
    )
