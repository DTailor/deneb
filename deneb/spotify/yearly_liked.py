"""Create spotify playlist with liked songs based on years"""
import datetime
from typing import List

from spotipy.client import SpotifyException

from deneb.chatbot.message import send_message
from deneb.config import Config
from deneb.db import User
from deneb.logger import get_logger, push_sentry_error
from deneb.sp import SpotifyYearlyStats, Spotter, spotify_client
from deneb.spotify.common import (
    _get_to_update_users, _user_task_filter, fetch_all, fetch_user_playlists,
    get_tracks, update_spotify_playlist
)
from deneb.structs import FBAlert, SpotifyKeys
from deneb.tools import run_tasks, search_dict_by_key

_LOGGER = get_logger(__name__)


def generate_playlist_name(year: str) -> str:
    """return a string of format `liked from <Year>`"""
    return f"liked from {year}"


def generate_tracks_to_add(
    liked_tracks: List[dict], playlist_tracks: List[dict]
) -> List[dict]:
    already_present_ids = [a["track"]["id"] for a in playlist_tracks]
    return [a for a in liked_tracks if a["id"] not in already_present_ids]


async def _sync_with_spotify_playlist(
    user: User, sp: Spotter, year: str, tracks: List[dict], dry_run: bool
) -> SpotifyYearlyStats:
    playlist_name = generate_playlist_name(year)

    user_playlists = await fetch_user_playlists(sp)
    _LOGGER.info(f"updating playlist: <{playlist_name}> for {user}")

    is_created, playlist = search_dict_by_key(playlist_name, user_playlists, "name")

    playlist_tracks = await get_tracks(sp, playlist) if is_created else []

    to_add_tracks = generate_tracks_to_add(tracks, playlist_tracks)
    if not dry_run:
        has_new_tracks = bool(to_add_tracks)
        if not is_created and has_new_tracks:
            playlist = await sp.client.user_playlist_create(
                sp.userdata["id"], playlist_name, public=False
            )

        if has_new_tracks:
            await update_spotify_playlist(
                to_add_tracks, playlist["uri"], sp, insert_top=True
            )

    if not playlist:
        playlist = {"name": playlist_name}

    stats = SpotifyYearlyStats(user.fb_id, playlist, {"tracks": to_add_tracks})

    _LOGGER.info(
        f"updated playlist: <{playlist_name}> for {user} | {stats.describe(brief=True)}"
    )
    return stats


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
            stats = await _sync_with_spotify_playlist(user, sp, year, tracks, dry_run)

            if fb_alert.notify and stats.has_new_tracks():
                await send_message(user.fb_id, fb_alert, stats.describe())
    except SpotifyException as exc:
        _LOGGER.exception(f"{user} failed to save liked songs by year")
        push_sentry_error(exc, user.username, user.display_name)
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
