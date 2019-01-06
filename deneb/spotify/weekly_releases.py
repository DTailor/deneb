"""Create spotify playlist with weekly new releases"""
import calendar
from datetime import datetime as dt
from datetime import timedelta
from itertools import chain
from math import ceil
from typing import Dict, List, Optional, Tuple  # noqa:F401

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
    return AlbumTracks(album_data, tracks)


def generate_tracks_to_add(
    sp: Spotter, db_tracks: List[Album], pl_tracks: List[dict]
) -> Tuple[List[AlbumTracks], List[AlbumTracks]]:
    """return list of tracks to be added"""
    already_present_tracks = {a["track"]["id"] for a in pl_tracks}

    # there are three types of releases to keep an eye on
    # 1. album tracks - the main focus of this app is to report new album tracks
    #                   and add work that data out later
    # 2. pre-album tracks - these are from an upcoming album. This include in them
    #                   eps, singles, etc.
    # 3. featured tracks - also there are releases from an artist which
    #                   is a feature on a different artist's song. Also
    #                   there are compilations and other unexplored album
    #                   types. These can keep coming from different artists
    #                   you follow, but still being on the same album. It's like
    #                   an indirect linked album to the artist.
    #                   Why Dict[str, AlbumTracks] ?
    #                   Track coming from different artists are respectively stored
    #                   under different album all pointing to the same one (maybe do this
    #                   at an earlier step?) and need to be only under ONE. This way we know
    #                   from which album is what by having the key.
    # Both first and second types are group in a list are called main_albums.
    # The third one is like a bonus, called featuring_albums

    main_albums = []  # type: List[AlbumTracks]
    featuring_albums = {}  # type: Dict[str, AlbumTracks]

    for item in db_tracks:
        is_album = item.type == "album"
        if is_album:
            album = get_album_tracks(sp, item)
        else:
            track = sp.client.track(item.uri)
            album = AlbumTracks(track["album"], [track])

        # we want albums with less than 3 tracks to be listed as tracks
        # because often they contain just remixes with 1 song or so.
        # figure out later how to spot this things and have a smarter handling
        # for albums which indeed have 3 different songs
        if is_album and len(album.tracks) > 3:
            # clean list of duplicates
            album.tracks = [
                a for a in album.tracks if a["id"] not in already_present_tracks
            ]
            # update list with new ids
            already_present_tracks.update({a["id"] for a in album.tracks})
            # add album to albums list if has songs to show
            if album.tracks:
                main_albums.append(album)
            continue

        for track in album.tracks:
            if track["id"] in already_present_tracks or album in main_albums:
                continue

            # in an album with less than 3 tracks
            if album.parent["id"] not in featuring_albums:
                featuring_albums[album.parent["id"]] = album
                already_present_tracks.update({a["id"] for a in album.tracks})
            else:
                featuring_albums[album.parent["id"]].tracks.append(track)
                already_present_tracks.add(track["id"])

    orphan_albums = list(featuring_albums.values())
    return main_albums, orphan_albums


def update_user_playlist(
    user: User, sp: Spotter, dry_run: Optional[bool] = False
) -> SpotifyStats:
    today = dt.now()
    monday = today - timedelta(days=today.weekday())
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

    tracks_from_albums = [a.tracks for a in albums]
    tracks_without_albums = [a.tracks for a in tracks]

    if not dry_run:
        for album_ids in grouper(
            100, chain(*tracks_from_albums, *tracks_without_albums)
        ):
            album_ids = clean(album_ids)
            album_ids = [a["id"] for a in album_ids]
            try:
                sp.client.user_playlist_add_tracks(
                    sp.userdata["id"], playlist["uri"], album_ids
                )
            except Exception as exc:
                _LOGGER.exception(f"add to playlist '{album_ids}' failed with: {exc}")
    albums_and_tracks = {"albums": albums, "tracks": tracks}
    stats = SpotifyStats(user.fb_id, playlist, albums_and_tracks)
    return stats


def update_users_playlists(
    credentials: SpotifyKeys,
    fb_alert: FBAlert,
    user_id: Optional[str],
    dry_run: Optional[bool],
):
    users = User.select()

    if user_id:
        users = [User.get(User.username == user_id)]

    for user in users:
        if not user.spotify_token:
            _LOGGER.info(f"can't update {user}, token not present.")
            continue

        with spotify_client(credentials, user) as sp:
            stats = update_user_playlist(user, sp, dry_run)
            if fb_alert.notify:
                send_message(user.fb_id, fb_alert, stats.describe())
