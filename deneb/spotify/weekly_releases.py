"""Create spotify playlist with weekly new releases"""
import calendar
from datetime import datetime as dt
from itertools import chain
from math import ceil
from typing import List, Optional, Tuple

from deneb.chatbot.message import send_message
from deneb.db import Album, User
from deneb.logger import get_logger
from deneb.sp import SpotifyStats, Spotter, spotify_client
from deneb.structs import AlbumTracks, FBAlert, SpotifyKeys
from deneb.tools import clean, fetch_all, grouper, is_present

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


def get_album_tracks(sp: Spotter, album: Album) -> AlbumTracks:
    tracks = []  # type: List[dict]
    album_data = sp.client.album(album.uri)
    tracks = fetch_all(sp, album_data["tracks"])
    return AlbumTracks(album, tracks)


def generate_tracks_to_add(
    sp: Spotter, db_tracks: List[Album], pl_tracks: List[dict]
) -> Tuple[List[AlbumTracks], List[AlbumTracks]]:
    """return list of tracks to be added"""
    already_present_tracks = {a["track"]["id"] for a in pl_tracks}

    albums = []
    tracks = []

    for item in db_tracks:
        if item.type == "album":
            album = get_album_tracks(sp, item)
        else:
            album = AlbumTracks(None, [sp.client.track(item.uri)])

        # we want albums with less than 3 tracks to be listed as tracks
        # because often they contain just remixes with 1 song or so.
        # figure out later how to spot this things and have a smarter handling
        # for albums which indeed have 3 different songs
        if album.parent and len(album.tracks) > 3:
            # clean list of duplicates
            album.tracks = [a for a in album.tracks if a['id'] not in already_present_tracks]
            # update list with new ids
            already_present_tracks.update({a["id"] for a in album.tracks})
            # add album to albums list if has songs to show
            if album.tracks:
                albums.append(album)
            continue

        for track in album.tracks:
            if track["id"] in already_present_tracks:
                continue
            tracks.append(album)
            already_present_tracks.add(track["id"])

    return albums, tracks


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
    albums, tracks = generate_tracks_to_add(sp, week_tracks_db, playlist_tracks)

    all_ids = []  # type: List[str]
    tracks_from_albums = [a.tracks for a in albums]
    tracks_without_albums = [a.tracks for a in tracks]

    for album_ids in grouper(100, chain(*tracks_from_albums, *tracks_without_albums)):
        album_ids = clean(album_ids)
        album_ids = [a["id"] for a in album_ids]
        try:
            sp.client.user_playlist_add_tracks(
                sp.userdata["id"], playlist["uri"], album_ids
            )
            all_ids.extend(album_ids)
        except Exception as exc:
            _LOGGER.exception(f"add to playlist '{album_ids}' failed with: {exc}")
    albums_and_tracks = {"albums": albums, "tracks": tracks}
    stats = SpotifyStats(user.fb_id, playlist, albums_and_tracks)
    return stats


def update_users_playlists(
    credentials: SpotifyKeys, fb_alert: FBAlert, user_id: Optional[str]
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
            if fb_alert.notify:
                send_message(user.fb_id, fb_alert, stats.describe())
