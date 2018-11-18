"""Create spotify playlist with weekly new releases"""
import calendar
from datetime import datetime as dt
from math import ceil
from typing import Any, List, Optional, Tuple

from db import Album, get_or_create_user
from logger import get_logger
from sp import Spotter, get_sp_client
from tools import fetch_all, is_present

_LOGGER = get_logger(__name__)


def week_of_month(dt: dt) -> int:
    """ Returns the week of the month for the specified date.
    """

    first_day = dt.replace(day=1)

    dom = dt.day
    adjusted_dom = dom + first_day.weekday()

    return int(ceil(adjusted_dom/7.0))


def generate_playlist_name() -> str:
    """return a string of format <Month> W<WEEK_NR> <Year>"""
    now = dt.now()
    month_name = calendar.month_name[now.month]
    week_nr = week_of_month(now)
    return f"{month_name} W{week_nr} {now.year}"


def fetch_user_playlists(sp: Spotter) -> List[Optional[dict]]:
    """Return user playlists"""
    playlists = []  # type: List[Optional[dict]]
    sp.client.user_playlist(sp.username)
    data = sp.client.user_playlists(sp.username)
    playlists = fetch_all(sp, data)
    return playlists


def get_tracks(sp: Spotter, playlist: dict) -> Optional[List[dict]]:
    """return playlist tracks"""
    tracks = sp.client.user_playlist(
        sp.username, playlist['id'], fields="tracks,next")['tracks']
    return fetch_all(sp, tracks)


def get_album_tracks(sp: Spotter, album: Album) -> List[dict]:
    tracks = []     # type: List[dict]
    album_data = sp.client.album(album.uri)
    tracks = fetch_all(sp, album_data["tracks"])
    return tracks


def generate_tracks_to_add(
    sp: Spotter,
    db_tracks: List[Album],
    pl_tracks: List[dict]
) -> List[Tuple[str, Any]]:
    """return list of tracks to be added"""
    already_present_tracks = {a["track"]["name"] for a in pl_tracks}

    tracks = []     # type: List[Tuple[str, Any]]
    for item in db_tracks:
        check_tracks = [item]
        if item.type == "album":
            check_tracks = get_album_tracks(sp, item)
        for track in check_tracks:
            if isinstance(track, Album):
                track_name = track.name
                track_id = track.spotify_id
            else:
                track_name = track["name"]
                track_id = track["id"]
            if track_name in already_present_tracks:
                continue
            tracks.append((track_id, track))
    return tracks


def main(username, fb_id):
    _LOGGER.info('')
    _LOGGER.info('------------ RUN ---------------')
    _LOGGER.info('')

    # fetch new releases for current user
    user, _ = get_or_create_user(fb_id)
    today = dt.now()
    monday_date = today.day - today.weekday()
    monday = today.replace(day=monday_date)
    week_tracks_db = user.released_from_weekday(monday)

    sp, token = get_sp_client(username)
    playlist_name = generate_playlist_name()

    # fetch or create playlist
    user_playlists = fetch_user_playlists(sp)
    playlist = is_present(playlist_name, user_playlists, 'name')
    if not playlist:
        playlist = sp.client.user_playlist_create(sp.username, playlist_name)
    playlist_tracks = get_tracks(sp, playlist)
    tracks = generate_tracks_to_add(sp, week_tracks_db, playlist_tracks)
    for track_id, track in tracks:
        # at the moment add every single track separately
        # there are some wrong ids on the way which break the
        # whole batch of ids
        # TODO: validate somehow the ids from the batch
        try:
            sp.client.user_playlist_add_tracks(sp.username, playlist['uri'], [track_id])
        except Exception as exc:
            _LOGGER.exception(f"trying to add {track} tracks: ; failed: {exc}")
