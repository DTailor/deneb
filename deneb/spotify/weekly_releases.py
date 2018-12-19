"""Create spotify playlist with weekly new releases"""
import calendar
from datetime import datetime as dt
from itertools import chain
from math import ceil
from typing import Dict, List, Optional

from deneb.chatbot.message import send_message
from deneb.db import Album, User
from deneb.logger import get_logger
from deneb.sp import Spotter, spotify_client
from deneb.structs import Chatboi, SpotifyKeys, SpotifyStats
from deneb.tools import (
    DefaultOrderedDict, clean, fetch_all, grouper, is_present
)

_LOGGER = get_logger(__name__)


def week_of_month(dt: dt) -> int:
    """ Returns the week of the month for the specified date.
    """

    first_day = dt.replace(day=1)

    dom = dt.day
    adjusted_dom = dom + first_day.weekday()

    return int(ceil(adjusted_dom / 7.0))


def generate_playlist_name() -> str:
    """return a string of format <Month> W<WEEK_NR> <Year>"""
    now = dt.now()
    month_name = calendar.month_name[now.month]
    week_nr = week_of_month(now)
    return f"{month_name} W{week_nr} {now.year}"


def fetch_user_playlists(sp: Spotter) -> List[dict]:
    """Return user playlists"""
    playlists = []  # type: List[dict]
    sp.client.user_playlist(sp.userdata["id"])
    data = sp.client.user_playlists(sp.userdata["id"])
    playlists = fetch_all(sp, data)
    return playlists


def get_tracks(sp: Spotter, playlist: dict) -> List[dict]:
    """return playlist tracks"""
    tracks = sp.client.user_playlist(
        sp.userdata["id"], playlist["id"], fields="tracks,next"
    )["tracks"]
    return fetch_all(sp, tracks)


def get_album_tracks(sp: Spotter, album: Album) -> List[dict]:
    tracks = []  # type: List[dict]
    album_data = sp.client.album(album.uri)
    tracks = fetch_all(sp, album_data["tracks"])
    return tracks


def generate_tracks_to_add(
    sp: Spotter, db_tracks: List[Album], pl_tracks: List[dict]
) -> Dict[str, DefaultOrderedDict]:
    """return list of tracks to be added"""
    already_present_tracks = {a["track"]["name"] for a in pl_tracks}

    tracks = {"album": DefaultOrderedDict(list), "track": DefaultOrderedDict(list)}
    for item in db_tracks:
        if item.type == "album":
            check_tracks = get_album_tracks(sp, item)
        else:
            check_tracks = [sp.client.track(item.uri)]
        for track in check_tracks:
            track_type = item.type
            if isinstance(track, Album):
                track_name = track.name
                track_id = track.spotify_id
            else:
                track_name = track["name"]
                track_id = track["id"]
            if track_name in already_present_tracks:
                continue
            else:
                already_present_tracks.add(track_name)
            if len(check_tracks) <= 3:
                # put all <= 3 track albums to tracks list
                track_type = "track"
            tracks[track_type][track_id].append(track)

    return tracks


def update_user_playlist(user: User, sp: Spotter) -> SpotifyStats:
    today = dt.now()
    monday_date = today.day - today.weekday()
    monday = today.replace(day=monday_date)
    week_tracks_db = user.released_from_weekday(monday)

    playlist_name = generate_playlist_name()

    # fetch or create playlist
    user_playlists = fetch_user_playlists(sp)
    _LOGGER.info(f"updating playlist: <{playlist_name}> for {user}")

    playlist = is_present(playlist_name, user_playlists, "name")
    if not playlist:
        playlist = sp.client.user_playlist_create(
            sp.userdata["id"], playlist_name, public=False
        )
    playlist_tracks = get_tracks(sp, playlist)
    tracks = generate_tracks_to_add(sp, week_tracks_db, playlist_tracks)

    all_ids = []                                                            # type: List[str]
    for album_ids in grouper(
        100, chain(tracks["album"].keys(), tracks["track"].keys())
    ):
        album_ids = clean(album_ids)
        try:
            sp.client.user_playlist_add_tracks(
                sp.userdata["id"], playlist["uri"], album_ids
            )
            all_ids.extend(album_ids)
        except Exception as exc:
            _LOGGER.exception(f"add to playlist '{album_ids}' failed with: {exc}")

    stats = SpotifyStats(user.fb_id, playlist, all_ids)
    return stats


def update_users_playlists(
    credentials: SpotifyKeys,
    chatboi: Chatboi,
    user_id: Optional[str],
):
    users = User.select()

    if user_id:
        users = [User.get(User.username == user_id)]

    for user in users:
        if not user.spotify_token:
            _LOGGER.info(f"can't update {user}, token not present.")
            continue

        with spotify_client(credentials, user) as sp:
            stats = update_user_playlist(user, sp)
            if chatboi.notify:
                send_message(
                    user.fb_id,
                    chatboi.chatboi_url,
                    chatboi.chatboi_key,
                    stats.describe(),
                )
