"""Entry point to deneb spotify watcher"""

from typing import Any, Dict, List, Optional, Tuple  # noqa

import sentry_sdk
from spotipy.client import SpotifyException

from deneb.artist_update import get_new_releases
from deneb.config import Config
from deneb.db import Market, User
from deneb.logger import get_logger
from deneb.sp import spotify_client
from deneb.structs import SpotifyKeys
from deneb.tools import find_markets_in_hours, run_tasks
from deneb.user_update import fetch_user_followed_artists

_LOGGER = get_logger(__name__)


async def _update_user_artists(
    credentials: SpotifyKeys, user: User, force_update: bool, dry_run: bool
):
    """task to update user followed artists and artist albums"""
    try:
        async with spotify_client(credentials, user) as sp:
            new_follows, lost_follows = await fetch_user_followed_artists(
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
        sentry_sdk.capture_message(f"spotify fail: {exc} {user}", level="ERROR")


def _user_task_filter(args: Tuple[SpotifyKeys, User, bool]) -> bool:
    """filter for task runner to check if task should be run"""
    if args[1].spotify_token:
        return True
    return False


async def _get_to_update_users(
    username: Optional[str] = None, all_markets: Optional[bool] = False
) -> List[User]:
    """if `--username` option used, fetch that user else fetch all users"""
    args = dict()  # type: Dict[str, Any]
    if username is not None:
        args["username"] = username

    if not all_markets:
        markets = await Market.all()
        active_markets = find_markets_in_hours(markets, [0, 12])
        args["market_id__in"] = [a.id for a in active_markets]

    users = []  # type: List[User]
    try:
        users = await User.filter(**args)
    except Exception as exc:
        sentry_sdk.capture_message(f"user select fail: {exc} {args}", level="ERROR")
    return users


async def update_users_artists(
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
