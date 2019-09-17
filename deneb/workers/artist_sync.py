"""Module to handle artist related updates"""
import datetime
import time
from functools import partial
from typing import Dict, Iterable, List, Tuple

import sentry_sdk
from spotipy import Spotify

from deneb.config import Config
from deneb.db import Album, Artist, PoolTortoise
from deneb.logger import get_logger
from deneb.spotify.common import fetch_all
from deneb.tools import run_tasks, search_dict_by_key

_LOGGER = get_logger(__name__)


def should_fetch_more_albums(
    albums: List[Dict], to_check_album_types: List[str]
) -> Tuple[bool, List[Dict], List[str]]:
    """
    filter artist albums from current year only and return if more fetching
    required
    #TODO: add year as a function argument
    """
    required_year = str(datetime.datetime.now().year)
    validated_albums = []  # type: List[dict]
    for album in albums:
        if album["album_type"] in to_check_album_types:
            to_check_album_types.remove(album["album_type"])

        if required_year in album["release_date"]:
            validated_albums.append(album)
        else:
            if not to_check_album_types:
                return False, validated_albums, to_check_album_types

    return True, validated_albums, to_check_album_types


async def fetch_all_albums(sp: Spotify, data: dict) -> List[Dict]:
    # ok, so this new `to_check_album_types` is a hack to fix-up a problem
    # the issues constits in the fact the as we fetch albums
    # we retrieve several `album_types`, like `album`, `single`, `appears_on`
    # and they are returned back in descendant order by `release_date`, the catch
    # is that they are group, meaning that you'll then them ordered that way but
    # first the `albums`, then the `single` and `appears_on`. This made the script
    # to miss some `sinlge` and `appears_on` type of albums

    to_check_album_types = ["album", "single", "appears_on"]
    contents = []

    while True:
        should, albums, to_check_album_types = should_fetch_more_albums(
            data["items"], to_check_album_types
        )
        contents.extend(albums)
        if not should or not data["next"]:
            break
        data = await sp.client.next(data)  # noqa: B305

    # there are some duplicates, remove them
    contents = list({v["id"]: v for v in contents}.values())
    return contents


async def fetch_albums(sp: Spotify, artist: Artist, retry: bool = False) -> List[dict]:
    """fetches artist albums from spotify"""
    try:
        data = await sp.client.artist_albums(
            artist.spotify_id, limit=50, album_type="album,single,appears_on"
        )
        albums = await fetch_all_albums(sp, data)
    except Exception:
        sentry_sdk.capture_exception()

        if not retry:
            raise
        albums = await fetch_albums(sp, artist, retry=True)
    return albums


def is_in_artists_list(artist: Artist, item: dict) -> bool:
    """True if appears in artists list, else False"""
    is_present_in_list, _ = search_dict_by_key(artist.spotify_id, item["artists"], "id")
    return is_present_in_list


async def get_featuring_songs(sp: Spotify, artist: Artist, album: dict) -> List[dict]:
    """get feature tracks from an album for an artist"""
    tracks = await sp.client.album_tracks(album_id=album["id"], limit=50)
    tracks = await fetch_all(sp, tracks)
    feature_tracks = []

    for track in tracks:
        if is_in_artists_list(artist, track):
            # track has no release date, so grab it
            track["release_date"] = album["release_date"]
            track["release_date_precision"] = album["release_date_precision"]
            feature_tracks.append(track)
    return feature_tracks


async def update_album_marketplace(
    album: Album, new_marketplace_ids: Iterable[str], dry_run: bool = False
) -> None:
    """Update an album markeplaces with the newly fetched ones"""
    if dry_run:
        return

    old_markets = await album.markets.filter()
    old_markets_ids = {a.name for a in old_markets}
    new_marketplace_ids = set(new_marketplace_ids)

    to_add = new_marketplace_ids - old_markets_ids
    to_remove = old_markets_ids - new_marketplace_ids
    to_remove_markets = [a for a in old_markets if a in to_remove]

    if to_remove_markets:
        await album.markets.remove(*to_remove_markets)

    # hack to upsert markets -> speedup
    if to_add:
        pool = PoolTortoise.get_connection("default")
        async with pool.acquire_connection() as conn:
            async with conn.transaction():
                markets_ids = await conn.fetch(
                    f"""
                    SELECT id
                    FROM market
                    Where name in ({str(to_add)[1:-1]})
                    """
                )
                values = [f"({album.id}, {market['id']})" for market in markets_ids]

                await conn.execute(
                    f"""
                    INSERT INTO album_markets(album_id, market_id)
                    VALUES
                    {', '.join(values)}
                    ON CONFLICT DO NOTHING;
                    """
                )


async def handle_album_sync(album: dict, artist: Artist) -> Tuple[bool, Album]:
    db_album, created = await Album.get_or_create(album)
    has_artist = await db_album.artists.filter(id=artist.id)
    if not has_artist:
        await db_album.artists.add(artist)

    # update it's marketplaces, for availability
    # TODO: disabled because not using this stuff;
    # think of where should marketplace be used and if not, removed;
    # not that big of an issue at this point with unavailable songs in playlists;
    # await update_album_marketplace(db_album, album["available_markets"])
    return created, db_album


async def update_artist_albums(
    sp: Spotify, artist: Artist, dry_run: bool = False
) -> Tuple[Artist, List[Album]]:
    """update artist albums by adding them to the db"""
    albums = await fetch_albums(sp, artist)
    processed_albums = []

    for album in albums:
        if album["album_type"] == "compilation":
            # these types of albums are just a collection of already knows songs
            # places in a new compilation album; gonna skipe those for a while
            # until more control of the flow
            continue

        if not is_in_artists_list(artist, album):
            # Some releases are not directly related to the artist himself.
            # It happens that if an artist has some feature songs on an album
            # for a different artist, it will be returned to the artist in cause
            # as well, so that this function checks that, and returns only feature
            # songs if it's the case.
            tracks = await get_featuring_songs(sp, artist, album)
            processed_albums.extend(tracks)
        else:
            processed_albums.append(album)

    args_items = [(album, artist) for album in processed_albums]
    task_results = await run_tasks(
        Config.ALBUMS_TASKS_AMOUNT, args_items, handle_album_sync
    )

    try:
        await artist.update_synced_at()
    except Exception:
        sentry_sdk.capture_exception()

    new_inserts = [a for created, a in task_results if created]
    return artist, new_inserts


def _album_filter(force: bool, args: Tuple[Spotify, Artist]) -> bool:
    if force or args[1].can_update():
        return True
    return False


async def get_new_releases(
    sp: Spotify, artists: List[Artist], force_update: bool = False
) -> Tuple[int, int]:
    """update artists with released albums"""
    updated_nr = 0
    albums_nr = 0

    args_items = [(sp, a) for a in artists]

    tstart = time.time()
    filter_func = partial(_album_filter, force=force_update)
    task_results = await run_tasks(
        Config.ARTISTS_TASKS_AMOUNT, args_items, update_artist_albums, filter_func
    )
    elapsed_time = time.time() - tstart
    _LOGGER.info(
        f"finished {len(task_results)} get_new_releases jobs; total elapsed: {elapsed_time}s"
    )

    for artist, new_additions in task_results:
        if new_additions:
            albums_nr += len(new_additions)
            updated_nr += 1

    return albums_nr, updated_nr
