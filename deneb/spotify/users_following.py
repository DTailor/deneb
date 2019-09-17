"""Entry point to deneb spotify watcher"""

from typing import Any, Dict, List, Optional, Tuple  # noqa

import sentry_sdk
from spotipy.client import SpotifyException

from deneb.config import Config
from deneb.db import User
from deneb.logger import get_logger
from deneb.sp import spotify_client
from deneb.spotify.common import _get_to_update_users, _user_task_filter
from deneb.structs import SpotifyKeys
from deneb.tools import run_tasks
from deneb.workers.artist_sync import get_new_releases
from deneb.workers.user_sync import sync_user_followed_artists

_LOGGER = get_logger(__name__)


async def _update_user_artists(
    credentials: SpotifyKeys, user: User, force_update: bool, dry_run: bool
):
    """task to update user followed artists and artist albums"""
    try:
        async with spotify_client(credentials, user) as sp:
            new_follows, lost_follows = await sync_user_followed_artists(
                user, sp, dry_run
            )

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
    except SpotifyException as exc:
        _LOGGER.warning(f"spotify fail: {exc} {user}")
        sentry_sdk.capture_exception()


async def sync_users_artists(
    credentials: SpotifyKeys,
    user_id: Optional[str] = None,
    force_update: bool = False,
    dry_run: bool = False,
    all_markets: bool = False,
):
    """entry point for updating user artists and artist albums"""
    users = await _get_to_update_users(user_id, all_markets=all_markets)
    args_items = [(credentials, user, force_update, dry_run) for user in users]
    await run_tasks(
        Config.USERS_TASKS_AMOUNT, args_items, _update_user_artists, _user_task_filter
    )
