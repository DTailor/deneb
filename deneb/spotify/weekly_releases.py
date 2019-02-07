"""Create spotify playlist with weekly new releases"""
import calendar
from datetime import datetime as dt
from datetime import timedelta
from itertools import chain
from math import ceil
from typing import Dict, Iterator, List, Optional, Tuple  # noqa:F401

from deneb.chatbot.message import send_message
from deneb.db import User, Album
from deneb.logger import get_logger
from deneb.sp import SpotifyStats, Spotter, spotify_client
from deneb.structs import AlbumTracks, FBAlert, SpotifyKeys
from deneb.tools import clean, fetch_all, grouper, is_present
from perf import print_stats, timeit

_LOGGER = get_logger(__name__)


@timeit
def week_of_month(dt: dt) -> int:
    """ Returns the week of the month for the specified date.
    """

    first_day = dt.replace(day=1)

    dom = dt.day
    adjusted_dom = dom + first_day.weekday()

    return int(ceil(adjusted_dom / 7.0))


@timeit
def generate_playlist_name() -> str:
    """return a string of format <Month> W<WEEK_NR> <Year>"""
    now = dt.now()
    month_name = calendar.month_name[now.month]
    week_nr = week_of_month(now)
    return f"{month_name} W{week_nr} {now.year}"


@timeit
async def fetch_user_playlists(sp: Spotter) -> List[dict]:
    """Return user playlists"""
    playlists = []  # type: List[dict]
    data = await sp.client.user_playlists(sp.userdata["id"])
    playlists = await fetch_all(sp, data)
    return playlists


@timeit
async def get_tracks(sp: Spotter, playlist: dict) -> List[dict]:
    """return playlist tracks"""
    tracks = await sp.client.user_playlist(
        sp.userdata["id"], playlist["id"], fields="tracks,next"
    )
    return await fetch_all(sp, tracks["tracks"])


@timeit
async def get_album_tracks(sp: Spotter, album: Album) -> AlbumTracks:
    tracks = []  # type: List[dict]
    album_data = await sp.client.album(album.uri)
    tracks = await fetch_all(sp, album_data["tracks"])
    return AlbumTracks(album_data, tracks)


@timeit
def verify_already_present(
    album: AlbumTracks, already_present_tracks: set
) -> Tuple[AlbumTracks, set]:
    """helper method to clean up already present items from playlist and update it"""
    album.tracks = [a for a in album.tracks if a["id"] not in already_present_tracks]
    # update list with new ids
    already_present_tracks.update({a["id"] for a in album.tracks})
    return album, already_present_tracks


@timeit
async def generate_tracks_to_add(
    sp: Spotter, db_tracks: List[Album], pl_tracks: List[dict]
) -> Tuple[List[AlbumTracks], List[AlbumTracks], List[AlbumTracks]]:
    """return list of tracks to be added"""
    already_present_tracks = {a["track"]["id"] for a in pl_tracks}

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

    for item in db_tracks:
        is_album = item.type == "album"
        if is_album:
            album = await get_album_tracks(sp, item)
        else:
            track = await sp.client.track(item.uri)
            album = AlbumTracks(track["album"], [track])

        if album.parent["album_type"] == "compilation":
            # they are messed up, later let user configure if he wants them
            continue

        # we want albums with less than 3 tracks to be listed as tracks
        # because often they contain just remixes with 1 song or so.
        # figure out later how to spot this things and have a smarter handling
        # for albums which indeed have 3 different songs

        if is_album and len(album.tracks) > 2:
            album, already_present_tracks = verify_already_present(
                album, already_present_tracks
            )
            if album.tracks:
                main_albums.append(album)
            continue

        if album.parent["album_type"] == "single":
            album, already_present_tracks = verify_already_present(
                album, already_present_tracks
            )
            if album.tracks:
                singles.append(album)
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
    return singles, main_albums, orphan_albums


@timeit
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
        except Exception as exc:
            _LOGGER.exception(f"add to playlist '{album_ids}' failed with: {exc}")


@timeit
async def update_user_playlist(
    user: User, sp: Spotter, dry_run: Optional[bool] = False
) -> SpotifyStats:
    today = dt.now()
    monday = today - timedelta(days=today.weekday())
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

        insert_top = False
        if today.weekday() == 4:
            # it's friday the release day so intert today's things from the
            # beggining of the playlist as it's the most important release day
            # of the week
            insert_top = True

        await update_spotify_playlist(to_add_tracks, playlist["uri"], sp, insert_top)

    return stats


@timeit
async def update_users_playlists(
    credentials: SpotifyKeys,
    fb_alert: FBAlert,
    user_id: Optional[str],
    dry_run: Optional[bool],
):
    if user_id:
        users = await User.filter(username=user_id)
    else:
        users = await User.all()
    for user in users:
        if not user.spotify_token:
            _LOGGER.info(f"can't update {user}, token not present.")
            continue

        async with spotify_client(credentials, user) as sp:
            stats = await update_user_playlist(user, sp, dry_run)
            if fb_alert.notify:
                await send_message(user.fb_id, fb_alert, stats.describe())
    print_stats()
