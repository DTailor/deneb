"""Module to handle artist related updates"""
import time
from functools import partial
from typing import Iterable, List, Tuple

from spotipy import Spotify

from deneb.config import Config
from deneb.db import Album, Artist, PoolTortoise
from deneb.logger import get_logger
from deneb.tools import (
    fetch_all, fetch_all_albums, generate_release_date, is_present, run_tasks
)

_LOGGER = get_logger(__name__)


async def fetch_albums(sp: Spotify, artist: Artist, retry: bool = False) -> List[dict]:
    """fetches artist albums from spotify"""
    try:
        data = await sp.client.artist_albums(
            artist.spotify_id, limit=50, album_type="album,single,appears_on"
        )
        albums = await fetch_all_albums(sp, data)
    except Exception as exc:
        if not retry:
            raise
        albums = await fetch_albums(sp, artist, retry=True)
    return albums


def is_in_artists_list(artist: Artist, item: dict) -> bool:
    """True if appears in artists list, else False"""
    return bool(is_present(artist.spotify_id, item["artists"], "id"))


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


async def get_or_create_album(album: dict, dry_run: bool = False) -> Tuple[bool, Album]:
    """return db instance and create if new, with dry-run"""
    created = False
    try:
        db_album = await Album.get(spotify_id=album["id"])
    except Exception:
        release_date = generate_release_date(
            album["release_date"], album["release_date_precision"]
        )
        db_album = await Album.create(
            name=album["name"],
            release=release_date,
            type=album["type"],
            spotify_id=album["id"],
        )
        created = True
    return created, db_album


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
    created, db_album = await get_or_create_album(album)
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

    await artist.update_timestamp()

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
