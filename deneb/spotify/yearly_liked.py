"""Create spotify playlist with liked songs based on years"""
import datetime
from typing import List

import sentry_sdk
from spotipy.client import SpotifyException

from deneb.config import Config
from deneb.db import User
from deneb.logger import get_logger
from deneb.sp import Spotter, spotify_client
from deneb.spotify.users import _get_to_update_users, _user_task_filter
from deneb.spotify.weekly_releases import (
    fetch_user_playlists, search_dict_by_key, update_spotify_playlist
)
from deneb.structs import FBAlert, SpotifyKeys
from deneb.tools import fetch_all, run_tasks

_LOGGER = get_logger(__name__)


def generate_playlist_name(year: str) -> str:
    """return a string of format `liked from <Year>`"""
    return f"liked from {year}"


async def _sync_with_spotify_playlist(
    user: User, sp: Spotter, year: str, tracks: List[dict], dry_run: bool
):
    playlist_name = generate_playlist_name(year)

    user_playlists = await fetch_user_playlists(sp)
    _LOGGER.info(f"updating playlist: <{playlist_name}> for {user}")

    is_created, playlist = search_dict_by_key(playlist_name, user_playlists, "name")

    # playlist_tracks = await get_tracks(sp, playlist) if is_created else []

    # singles, albums, tracks = await generate_tracks_to_add(
    #     sp, week_tracks_db, playlist_tracks
    # )

    if not dry_run:
        has_new_tracks = bool(len(list(tracks)))
        if not is_created and has_new_tracks:
            playlist = await sp.client.user_playlist_create(
                sp.userdata["id"], playlist_name, public=False
            )

        if has_new_tracks:
            await update_spotify_playlist(tracks, playlist["uri"], sp, insert_top=True)


async def _sync_saved_from_year_playlist(
    user: User, sp: Spotter, year: str, dry_run: bool
) -> List[dict]:
    current_year_tracks = []
    all_liked_partial = await sp.client.current_user_saved_tracks()

    all_liked_songs = await fetch_all(sp, all_liked_partial)

    for item in all_liked_songs:
        if item["track"]["album"]["release_date"][:4] == year:
            current_year_tracks.append(item["track"])
    return current_year_tracks


async def _handle_saved_songs_by_year_playlist(
    credentials: SpotifyKeys, user: User, year: str, dry_run: bool, fb_alert: FBAlert
) -> None:
    try:
        async with spotify_client(credentials, user) as sp:
            tracks = await _sync_saved_from_year_playlist(user, sp, year, dry_run)
            await _sync_with_spotify_playlist(user, sp, year, tracks, dry_run)
            # if fb_alert.notify and stats.has_new_releases():
            #     await send_message(user.fb_id, fb_alert, stats.describe())
    except SpotifyException as exc:
        _LOGGER.warning(f"spotify fail: {exc} {user}")
        sentry_sdk.capture_exception()
    return


async def update_users_playlists_liked_by_year(
    credentials: SpotifyKeys,
    fb_alert: FBAlert,
    user_id: str = None,
    year: str = None,
    dry_run: bool = False,
) -> None:
    users = await _get_to_update_users(user_id, all_markets=True)

    if not year:
        year = str(datetime.datetime.now().year)

    args_items = [(credentials, user, year, dry_run, fb_alert) for user in users]
    await run_tasks(
        Config.USERS_TASKS_AMOUNT,
        args_items,
        _handle_saved_songs_by_year_playlist,
        _user_task_filter,
    )
