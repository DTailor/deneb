"""Create spotify playlist with weekly new releases"""
import calendar
from asyncio import sleep
from datetime import datetime as dt
from datetime import timedelta
from itertools import chain
from math import ceil
from typing import Dict, Iterator, List, Optional, Tuple  # noqa:F401

from spotipy.client import SpotifyException

from deneb.chatbot.message import send_message
from deneb.config import Config
from deneb.db import Album, User
from deneb.logger import get_logger
from deneb.sp import SpotifyStats, Spotter, spotify_client
from deneb.spotify.users import _get_to_update_users, _user_task_filter
from deneb.structs import AlbumTracks, FBAlert, SpotifyKeys
from deneb.tools import (
    clean,
    convert_to_date,
    fetch_all,
    grouper,
    is_present,
    run_tasks,
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


async def fetch_user_playlists(sp: Spotter) -> List[dict]:
    """Return user playlists"""
    playlists = []  # type: List[dict]
    data = await sp.client.user_playlists(sp.userdata["id"])
    playlists = await fetch_all(sp, data)
    return playlists


async def get_tracks(sp: Spotter, playlist: dict) -> List[dict]:
    """return playlist tracks"""
    tracks = await sp.client.user_playlist(
        sp.userdata["id"], playlist["id"], fields="tracks,next"
    )
    return await fetch_all(sp, tracks["tracks"])


async def _make_album_tracks(sp: Spotter, album: Album) -> AlbumTracks:
    tracks = []  # type: List[dict]
    album_data = await sp.client.album(album.uri)
    tracks = await fetch_all(sp, album_data["tracks"])
    return AlbumTracks(album_data, tracks)


def __update_already_present(already_present_tracks: set, album: AlbumTracks):
    already_present_tracks.update({a["name"] for a in album.tracks})


def _clean_update_playlist_already_present(
    album: AlbumTracks, already_present_tracks: set
) -> Tuple[AlbumTracks, set]:
    """helper method to clean up already present items from playlist and update it"""
    album.tracks = [a for a in album.tracks if a["name"] not in already_present_tracks]
    # update list with new ids
    __update_already_present(already_present_tracks, album)
    return album, already_present_tracks


async def _get_album_tracks(sp: Spotter, item: Album, is_album: bool) -> AlbumTracks:
    if is_album:
        album = await _make_album_tracks(sp, item)
    else:
        track = await sp.client.track(item.uri)
        album = AlbumTracks(track["album"], [track])
    return album


def _is_various_artists_album(album: dict) -> bool:
    if len(album["artists"]) and album["artists"][0]["name"] == "Various Artists":
        return True
    return False


async def generate_tracks_to_add(  # noqa
    sp: Spotter, db_albums: List[Album], pl_tracks: List[dict]
) -> Tuple[List[AlbumTracks], List[AlbumTracks], List[AlbumTracks]]:
    """return list of tracks to be added"""
    already_present_tracks = {a["track"]["name"] for a in pl_tracks}

    # there are three types of releases to keep an eye on
    # 1. singles - these are from an upcoming album. This includes in them
    #              singles. They are to be listed first at the moment, afterwards
    #              let the user decide the ordering
    # 2. album tracks - the main focus of this app is to report new album tracks
    #              and add work that data out later
    # 3. featured tracks - also there are releases from an artist which
    #              is a feature on a different artist's song.
    #              Why Dict[str, AlbumTracks] ?
    #              Track coming from different artists are respectively stored
    #              under different album all pointing to the same one (maybe do this
    #              at an earlier step?) and need to be only under ONE. This way we know
    #              from which album is what by having the key.
    singles = []  # type: List[AlbumTracks]
    main_albums = []  # type: List[AlbumTracks]
    featuring_albums = {}  # type: Dict[str, AlbumTracks]

    post_process_singles = []  # type: List[AlbumTracks]
    post_process_features = []  # type: List[AlbumTracks]

    for db_album in db_albums:
        is_album = db_album.type == "album"
        try:
            album = await _get_album_tracks(sp, db_album, is_album)
        except SpotifyException:
            _LOGGER.warning(f"failed to fetch {db_album} is_album:{is_album}")
            continue

        if sp.userdata["country"] not in album.parent["available_markets"]:
            continue
        # we want albums with less than 3 tracks to be listed as tracks
        # because often they contain just remixes with 1 song or so.
        # figure out later how to spot this things and have a smarter handling
        # for albums which indeed have 3 different songs
        if is_album and len(album.tracks) > 2:
            album, already_present_tracks = _clean_update_playlist_already_present(
                album, already_present_tracks
            )
            if album.tracks:
                main_albums.append(album)
        elif album.parent["album_type"] == "single":
            if not _is_various_artists_album(album.parent):
                post_process_singles.append(album)
            else:
                _LOGGER.warning(
                    f"discard {album.parent['album_type']} "
                    f"{album.parent['artists'][0]['name']} - {album.parent['name']} "
                    f"[{album.parent['uri']}]"
                )
        else:
            if not _is_various_artists_album(album.parent):
                post_process_features.append(album)
            else:
                _LOGGER.warning(
                    f"discard {album.parent['album_type']} "
                    f"{album.parent['artists'][0]['name']} - {album.parent['name']} "
                    f"[{album.parent['uri']}]"
                )

    for album in post_process_singles:
        album, already_present_tracks = _clean_update_playlist_already_present(
            album, already_present_tracks
        )
        if album.tracks:
            singles.append(album)

    for album in post_process_features:
        for track in remove_unwanted_tracks(album.tracks):
            if track["name"] in already_present_tracks:
                continue

            # in an album with less than 3 tracks
            if album.parent["id"] not in featuring_albums:
                featuring_albums[album.parent["id"]] = album
            else:
                featuring_albums[album.parent["id"]].tracks.append(track)

        __update_already_present(already_present_tracks, album)

    return singles, main_albums, list(featuring_albums.values())


async def update_spotify_playlist(
    tracks: Iterator, playlist_uri: str, sp: Spotter, insert_top: bool = False
):
    """Add the ids from track iterable to the playlist, insert_top bool does it
    on top of all the items, for fridays"""

    index = 0
    for album_ids in grouper(100, tracks):
        album_ids = clean(album_ids)
        album_ids = [a["id"] for a in album_ids]
        args = (sp.userdata["id"], playlist_uri, album_ids)

        if insert_top:
            args = args + (index,)  # type: ignore

        try:
            await sp.client.user_playlist_add_tracks(*args)
            index += len(album_ids) - 1
            await sleep(0.2)
        except Exception as exc:
            _LOGGER.exception(f"add to playlist '{album_ids}' failed with: {exc}")


def remove_unwanted_tracks(tracks: List[Dict]) -> List[Dict]:
    # remove low popularity tracks
    popular_tracks = [a for a in tracks if a["popularity"] > 40]  # type: ignore
    return sorted(  # type: ignore
        popular_tracks, key=lambda k: k["popularity"], reverse=True
    )


async def update_user_playlist(
    user: User,
    sp: Spotter,
    dry_run: Optional[bool] = False,
    debug: Optional[bool] = True,
) -> SpotifyStats:
    today = dt.now()
    monday = convert_to_date(today - timedelta(days=today.weekday()))
    week_tracks_db = await user.released_from_weekday(monday)
    playlist_name = generate_playlist_name()

    # fetch or create playlist
    user_playlists = await fetch_user_playlists(sp)
    _LOGGER.info(f"updating playlist: <{playlist_name}> for {user}")

    playlist = is_present(playlist_name, user_playlists, "name")
    if not playlist:
        playlist = await sp.client.user_playlist_create(
            sp.userdata["id"], playlist_name, public=False
        )

    playlist_tracks = await get_tracks(sp, playlist)
    singles, albums, tracks = await generate_tracks_to_add(
        sp, week_tracks_db, playlist_tracks
    )

    tracks_from_singles = [a.tracks for a in singles]
    tracks_from_albums = [a.tracks for a in albums]
    tracks_without_albums = [a.tracks for a in tracks]

    stats = SpotifyStats(
        user.fb_id, playlist, {"singles": singles, "albums": albums, "tracks": tracks}
    )

    if not dry_run:
        to_add_tracks = chain(
            *tracks_from_singles, *tracks_from_albums, *tracks_without_albums
        )

        is_friday = lambda: today.weekday() == 4  # noqa: E731
        # it's friday the release day so intert today's things from the
        # beggining of the playlist as it's the most important release day
        # of the week
        insert_top = True if is_friday() else False

        await update_spotify_playlist(to_add_tracks, playlist["uri"], sp, insert_top)

    _LOGGER.info(
        f"updated playlist: <{playlist_name}> for {user} | {stats.describe(brief=True)}"
    )
    return stats


async def _handle_update_user_playlist(
    credentials: SpotifyKeys, user: User, dry_run: bool, fb_alert: FBAlert
):
    async with spotify_client(credentials, user) as sp:
        stats = await update_user_playlist(user, sp, dry_run)
        if fb_alert.notify and stats.has_new_releases():
            await send_message(user.fb_id, fb_alert, stats.describe())


async def update_users_playlists(
    credentials: SpotifyKeys,
    fb_alert: FBAlert,
    user_id: Optional[str],
    dry_run: Optional[bool],
):
    users = await _get_to_update_users(user_id)
    args_items = [(credentials, user, dry_run, fb_alert) for user in users]
    await run_tasks(
        Config.USERS_TASKS_AMOUNT,
        args_items,
        _handle_update_user_playlist,
        _user_task_filter,
    )
