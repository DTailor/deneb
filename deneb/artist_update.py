"""Module to handle artist related updates"""
from typing import Iterable, List, Tuple
import asyncio
from spotipy import Spotify

from deneb.db import Album, Artist, Market
from deneb.logger import get_logger
from deneb.tools import (
    clean, fetch_all, generate_release_date, is_present
)

_LOGGER = get_logger(__name__)


async def fetch_albums(sp: Spotify, artist: Artist, retry: bool = False) -> List[dict]:
    """fetches artist albums from spotify"""
    try:
        # TODO: make async call
        data = sp.client.artist_albums(artist.spotify_id, limit=50)
        albums = await fetch_all(sp, data)
    except Exception as exc:
        if not retry:
            print(type(exc), exc, artist)
            raise
        albums = await fetch_albums(sp, artist, retry=True)
    return albums


class FetchDetailedAlbum:
    def __init__(self, sp: Spotify, albums: List[dict]) -> None:
        self.sp = sp
        self.albums = albums
        self.detailed_albums = asyncio.Queue()    # type: asyncio.Queue

    def __aiter__(self):
        return self

    async def fetch_update_albums(self, album_ids) -> None:
        # TODO: make async call
        data = self.sp.client.albums(albums=[a["id"] for a in album_ids])
        for album in data["albums"]:
            await self.detailed_albums.put(album)

    async def __anext__(self):
        if not self.detailed_albums.empty():
            return await self.detailed_albums.get()

        to_check_albums = clean(self.albums[:20])
        if not to_check_albums:
            raise StopAsyncIteration
        self.albums = self.albums[20:]

        await self.fetch_update_albums(to_check_albums)
        return await self.detailed_albums.get()


def is_in_artists_list(artist: Artist, item: dict) -> bool:
    """True if appears in artists list, else False"""
    return bool(is_present(artist.spotify_id, item["artists"], "id"))


async def get_featuring_songs(sp: Spotify, artist: Artist, album: dict) -> List[dict]:
    """get feature tracks from an album with the artist"""
    tracks = await fetch_all(sp, album["tracks"])
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


async def get_or_create_market(marketname: str, dry_run: bool = False) -> Market:
    """Retrieve or init marketplace instance"""
    try:
        market = await Market.get(Market.name == marketname)
    except Exception:
        market = await Market.create(market_name=marketname)

    return market


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

    for marketname in to_add:
        market, _ = await Market.get_or_create(name=marketname)
        await album.markets.add(market)


async def handle_album_sync(
    album: dict, artist: Artist
) -> Tuple[bool, Album]:
    created, db_album = await get_or_create_album(album)
    has_artist = await db_album.artists.filter(id=artist.id)
    if not has_artist:
        await db_album.artists.add(artist)

    # update it's marketplaces, for availability
    await update_album_marketplace(db_album, album["available_markets"])

    await db_album.update_timestamp()
    return created, db_album


def sync_with_db(
    albums: List[dict], artist: Artist
) -> List[asyncio.Future]:
    """Adds new albums to db, and returns db instances and new inserts"""
    tasks = [asyncio.create_task(handle_album_sync(a, artist)) for a in albums]
    return tasks


async def update_artist_albums(
    sp: Spotify, artist: Artist, dry_run: bool = False
) -> List[Album]:
    """update artist albums by adding them to the db"""
    albums = await fetch_albums(sp, artist)
    processed_albums = []
    async for detailed_album in FetchDetailedAlbum(sp, albums):
        if not is_in_artists_list(artist, detailed_album):
            # Some releases are not directly related to the artist himself.
            # It happens that if an artist has some feature songs on an album
            # for a different artist, it will be returned to the artist in cause
            # as well, so that this function checks that, and returns only feature
            # songs if it's the case.
            tracks = await get_featuring_songs(sp, artist, detailed_album)
            processed_albums.extend(tracks)
        else:
            processed_albums.append(detailed_album)

    new_inserts = []

    tasks = sync_with_db(processed_albums, artist)
    for task in asyncio.as_completed(tasks):    # type: asyncio.Future
        created, album = await task

        if created:
            new_inserts.append(album)

    await artist.update_timestamp()
    return artist, new_inserts

from itertools import islice
def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))


def make_artist_tasks(sp: Spotify, artists: List[Artist]) -> List[asyncio.Future]:
    return [asyncio.create_task(update_artist_albums(sp, a)) for a in artists]


async def get_new_releases(
    sp: Spotify, artists: Iterable[Artist], force_update: bool = False
) -> Tuple[int, int]:
    """update artists with released albums"""
    updated_nr = 0
    albums_nr = 0

    artist_jobs = []
    for artist in artists:
        if artist.can_update() or force_update:
            artist_jobs.append(artist)

        if len(artist_jobs) >= 10:

            tasks = make_artist_tasks(sp, artist_jobs)
            for task in asyncio.as_completed(tasks):
                artist, new_additions = await task

                if new_additions:
                    _LOGGER.info(f"fetched {len(new_additions)} albums for {artist}")
                    albums_nr += len(new_additions)
                    updated_nr += 1

            artist_jobs = []

    if artist_jobs:
        tasks = make_artist_tasks(sp, artist_jobs)

        for task in asyncio.as_completed(tasks):
            artist, new_additions = await task
            _LOGGER.info(f"fetched {len(new_additions)} albums for {artist}")

            if new_additions:
                albums_nr += len(new_additions)
                updated_nr += 1
