"""Entry point to deneb spotify watcher"""

from typing import Any, Dict, List, Optional, Tuple  # noqa

from tenacity import retry, stop_after_attempt, wait_fixed

from deneb.config import Config
from deneb.db import User
from deneb.logger import get_logger, push_sentry_error
from deneb.sp import spotify_client
from deneb.spotify.common import _get_to_update_users, _user_task_filter
from deneb.structs import SpotifyKeys, WeeklyPlaylistUpdateConfig
from deneb.tools import run_tasks
from deneb.workers.artist_sync import get_new_releases
from deneb.workers.user_sync import sync_user_followed_artists

_LOGGER = get_logger(__name__)

_CONFIG_ID = "weekly-playlist-update"


@retry(
    reraise=True,
    stop=stop_after_attempt(Config.JOB_MAX_ATTEMPTS_RETRY),
    wait=wait_fixed(Config.JOB_WAIT_RETRY),
)
async def _update_user_artists(
    credentials: SpotifyKeys, user: User, force_update: bool, dry_run: bool
):
    """task to update user followed artists and artist albums"""
    user_config = WeeklyPlaylistUpdateConfig(**user.config[_CONFIG_ID])
    if not user_config.enabled:
        return
    sp = None
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
    except Exception as exc:
        _LOGGER.exception(f"{user} failed to update artists")
        user_id = None
        username = None
        if sp:
            user_id = sp.userdata["id"]
            username = sp.userdata["display_name"]
        push_sentry_error(exc, user_id, username)


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
