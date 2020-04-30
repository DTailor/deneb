"""Create spotify playlist with liked songs based on years"""
import datetime
from typing import List, Optional

from spotipy.client import SpotifyException

from deneb.chatbot.message import send_message
from deneb.config import Config
from deneb.db import User
from deneb.logger import get_logger, push_sentry_error
from deneb.sp import SpotifyYearlyStats, Spotter, spotify_client
from deneb.spotify.common import (
    _get_to_update_users, _user_task_filter, fetch_all, fetch_user_playlists,
    update_spotify_playlist
)
from deneb.structs import FBAlert, LikedSortedYearlyConfig, SpotifyKeys
from deneb.tools import run_tasks, search_dict_by_key

_LOGGER = get_logger(__name__)

_CONFIG_ID = "liked-sorted-yearly"


def generate_playlist_name(year: str) -> str:
    """return a string of format `liked from <Year>`"""
    return f"liked from {year}"


def generate_tracks_to_add(
    liked_tracks: List[dict], playlist_tracks: List[dict]
) -> List[dict]:
    already_present_ids = [a["track"]["id"] for a in playlist_tracks]
    return [a for a in liked_tracks if a["id"] not in already_present_ids]


async def _sync_with_spotify_playlist(
    user: User,
    sp: Spotter,
    new_tracks: List[dict],
    playlist: dict,
    playlist_name: str,
    dry_run: bool,
) -> SpotifyYearlyStats:
    if not dry_run:
        has_new_tracks = bool(new_tracks)
        if not playlist and has_new_tracks:
            playlist = await sp.client.user_playlist_create(
                sp.userdata["id"], playlist_name, public=False
            )

        if has_new_tracks:
            await update_spotify_playlist(
                new_tracks, playlist["uri"], sp, insert_top=True
            )

    stats = SpotifyYearlyStats(user.fb_id, playlist, {"tracks": new_tracks})

    _LOGGER.info(
        f"updated playlist: <{playlist_name}> for {user} | {stats.describe(brief=True)}"
    )
    return stats


async def _fetch_year_tracks_from_saved(
    user: User, sp: Spotter, year: str, last_added_track_id: str = None
) -> List[dict]:
    current_year_tracks = []
    all_liked_partial = await sp.client.current_user_saved_tracks()

    all_liked_songs = await fetch_all(sp, all_liked_partial)

    for item in all_liked_songs:
        if item["track"]["id"] == last_added_track_id:
            break

        if item["track"]["album"]["release_date"][:4] == year:
            current_year_tracks.append(item["track"])

    return current_year_tracks


async def _handle_saved_songs_by_year_playlist(
    credentials: SpotifyKeys, user: User, year: str, dry_run: bool, fb_alert: FBAlert
) -> None:
    """Main task runner which will:
        - fetch playlist based on year and it's tracks
        - fetch first first batch of tracks from playlist if exists
        - first (which is last added) track is used as stop point for
          fetching liked tracks
        - fetch liked tracks up to last added track id previously fetched
        - sync with playlist (and create if non-existent) new tracks
    """
    user_config = LikedSortedYearlyConfig(**user.config[_CONFIG_ID])
    if not user_config.enabled:
        return
    try:
        async with spotify_client(credentials, user) as sp:
            # fetch playlist if exist and get last added track as reference
            # to when to stop seeking in liked songs
            playlist_name = generate_playlist_name(year)
            user_playlists = await fetch_user_playlists(sp)

            is_created, playlist = search_dict_by_key(
                playlist_name, user_playlists, "name"
            )

            # not using `get_tracks` because there's need for the first item
            # from first batch only
            playlist_tracks = (
                await sp.client.user_playlist(
                    sp.userdata["id"], playlist["id"], fields="tracks,next"
                )
                if is_created
                else {}
            )

            # unpack tracks
            playlist_tracks = playlist_tracks.get("tracks", {}).get("items", [])

            # last added track if so
            last_added_track_id = None

            if playlist_tracks:
                last_added_track_id = playlist_tracks[0]["track"]["id"]

            _LOGGER.info(f"updating playlist: <{playlist_name}> for {user}")

            new_tracks = await _fetch_year_tracks_from_saved(
                user, sp, year, last_added_track_id
            )
            stats = await _sync_with_spotify_playlist(
                user, sp, new_tracks, playlist, playlist_name, dry_run
            )

            if fb_alert.notify and stats.has_new_tracks():
                await send_message(user.fb_id, fb_alert, stats.describe())
    except Exception as exc:
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
