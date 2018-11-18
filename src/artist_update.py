"""Module to handle artist related updates"""
from typing import Iterable, List, Optional, Tuple

from spotipy import Spotify

from db import Album, Artist, Market
from logger import get_logger
from tools import clean, fetch_all, generate_release_date, grouper, is_present

_LOGGER = get_logger(__name__)


def fetch_albums(
        sp: Spotify,
        artist: Artist,
        retry: bool = False
) -> List[Optional[dict]]:
    """fetches artist albums from spotify"""
    try:
        data = sp.client.artist_albums(artist.spotify_id, limit=50)
        albums = fetch_all(sp, data)
    except Exception as exc:
        if not retry:
            print(type(exc), exc, artist)
            raise
        albums = fetch_albums(artist, True)
    return albums


def fetch_detailed_album(sp: Spotify, albums: Album) -> Iterable[dict]:
    """Fetch detailed album view from spotify for a simplified album list"""
    for albums_chunk in grouper(20, albums):
        albums_chunk = clean(albums_chunk)
        data = sp.client.albums(albums=[a['id'] for a in albums_chunk])
        for album in data['albums']:
            yield album


def is_in_artists_list(artist: Artist, item: dict) -> bool:
    """True if appears in artists list, else False"""
    return is_present(artist.spotify_id, item['artists'], 'id')


def get_featuring_songs(
        sp: Spotify, artist: Artist, album: dict
) -> List[dict]:
    """get feature tracks from an album with the artist"""
    tracks = fetch_all(sp, album['tracks'])
    feature_tracks = []

    for track in tracks:
        if is_in_artists_list(artist, track):
            # track has no release date, so grab it
            track['release_date'] = album['release_date']
            track['release_date_precision'] = album['release_date_precision']
            feature_tracks.append(track)
    return feature_tracks


def get_or_create_album(
        album: dict,
        dry_run: bool = False
) -> Album:
    """return db instance and create if new, with dry-run"""
    created = False
    try:
        db_album = Album.get(spotify_id=album['id'])
    except Exception:
        release_date = generate_release_date(
            album['release_date'],
            album['release_date_precision']
            )
        db_album = Album.save_to_db(
            name=album['name'], release_date=release_date,
            a_type=album['type'], spotify_id=album['id'],
            no_db=dry_run
        )
        created = True
    return created, db_album


def get_or_create_market(marketname: str, dry_run: bool = False) -> Market:
    """Retrieve or init marketplace instance"""
    try:
        market = Market.get(Market.name == marketname)
    except Exception:
        market = Market.save_to_db(market_name=marketname, no_db=dry_run)

    return market


def update_album_marketplace(
        album: Album,
        new_marketplace_ids: Iterable[str],
        dry_run: bool = False
) -> None:
    """Update an album markeplaces with the newly fetched ones"""
    old_markets = [a for a in album.get_markets()]
    old_markets_ids = set([a.name for a in old_markets])
    new_marketplace_ids = set(new_marketplace_ids)

    to_add = new_marketplace_ids - old_markets_ids
    to_remove = old_markets_ids - new_marketplace_ids

    if dry_run:
        return

    for old_market in old_markets:
        if old_market.name in to_remove:
            album.remove_market(old_market)

    for marketname in to_add:
        market = get_or_create_market(marketname)
        album.add_market(market)


def sync_with_db(
        albums: List[dict],
        artist: Artist,
        dry_run: bool = False
) -> Tuple[List[Album], List[Album]]:
    """Adds new albums to db, and returns db instances and new inserts"""
    db_albums = []      # type: list
    new_inserts = []

    for album in albums:
        # get or init album
        created, db_album = get_or_create_album(album, dry_run)
        db_albums.append(db_albums)
        if created:
            new_inserts.append(db_album)

        if not db_album.has_artist(artist):
            db_album.add_artist(artist)

        # update it's marketplaces, for availability
        update_album_marketplace(db_album, album['available_markets'])
        db_album.update_timestamp()

    return db_albums, new_inserts


def update_artist_albums(
        sp: Spotify,
        artist: Artist,
        dry_run: bool = False
) -> List[dict]:
    """update artist albums by adding them to the db"""
    albums = fetch_albums(sp, artist)
    processed_albums = []
    for detailed_album in fetch_detailed_album(sp, albums):
        if not is_in_artists_list(artist, detailed_album):
            # Some releases are not directly related to the artist himself.
            # It happens that if an artist has some feature songs on an album
            # for a different artist, it will be returned to the artist in cause
            # as well, so that this function checks that, and returns only feature
            # songs if it's the case.
            tracks = get_featuring_songs(sp, artist, detailed_album)
            processed_albums.extend(tracks)
        else:
            processed_albums.append(detailed_album)

    _, new_inserts = sync_with_db(processed_albums, artist, dry_run)

    return new_inserts


def get_new_releases(sp: Spotify, dry_run: bool = False) -> None:
    """update artists with released albums"""
    updated_nr = 0
    albums_nr = 0
    for artist in Artist.select():
        if artist.can_update():
            _LOGGER.info(f"start update for {artist}")
            new_additions = update_artist_albums(sp, artist, dry_run)
            if new_additions:
                _LOGGER.info(f"{len(new_additions)} fetched for {artist}")
                albums_nr += len(new_additions)
            artist.update_timestamp()
            updated_nr += 1

    _LOGGER.info(f"fetched {albums_nr} for {updated_nr} artists")
