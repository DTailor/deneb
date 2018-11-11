"""Module to handle artist related updates"""
import datetime

from spotipy import Spotify

from db import Album, Artist  # pylint: disable=import-error
from tools import grouper, clean, is_present


def fetch_all(sp_client: Spotify, data: dict) -> list:
    """iterates till gets all the albums"""
    contents = []
    while data:
        contents.extend(data["items"])
        data = sp_client.next(data)
    return contents


def fetch_albums(
        sp_client: Spotify,
        artist: Artist,
        retry: bool = False
) -> [Album]:
    """fetches artist albums from spotify"""
    try:
        data = sp_client.artist_albums(artist.spotify_id, limit=50)
        albums = fetch_all(sp_client, data)
    except Exception as exc:
        if not retry:
            print(type(exc), exc, artist)
            raise
        albums = fetch_albums(artist, True)
    return albums



def fetch_detailed_album(sp_client: Spotify, albums: Album) -> dict:
    for albums_chunk in grouper(20, albums):
        albums_chunk = clean(albums_chunk)
        data = sp_client.albums(albums=[a['id'] for a in albums_chunk])
        for album in data['albums']:
            yield album


def is_in_artists_list(artist: Artist, item: dict) -> bool:
    """True if appears in artists list, else False"""
    return is_present(artist.spotify_id, item['artists'], 'id')


def get_featuring_songs(
    sp_client: Spotify, artist: Artist, album: dict
) -> [dict]:
    """get feature tracks from an album with the artist"""
    tracks = fetch_all(sp_client, album['tracks'])
    feature_tracks = []

    for track in tracks:
        if is_in_artists_list(artist, track):
            feature_tracks.append(track)

    return feature_tracks


def generate_release_date(date: str, precision: str) -> datetime.datetime:
    suffix = {
        'year': '-01-01',
        'month': '-01',
        'day': ''
    }
    return datetime.datetime.strptime(
        '{}{}'.format(date, suffix[precision]), '%Y-%m-%d')


def get_or_create_album(
        album: dict,
        dry_run: bool = False
) -> Album:
    """return db instance and create if new, with dry-run"""
    created = False
    try:
        db_album = Album.get(spotify_id=album['id'])
    except:
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


def sync_with_db(
        albums: [dict],
        dry_run: bool = False
) -> [Album]:
    """Adds new albums to db, and returns the inserts"""
    new_inserts = []

    for album in albums:
        created, db_album = get_or_create_album(album, dry_run)
        if created:
            new_inserts.append(db_album)
    return new_inserts


def update_artist_albums(
        sp_client: Spotify,
        artist: Artist,
        dry_run: bool = False
) -> None:
    """update artist albums by adding them to the db"""
    albums = fetch_albums(sp_client, artist)
    processed_albums = []
    for detailed_album in fetch_detailed_album(sp_client, albums):
        if not is_in_artists_list(artist, detailed_album):
            # Some releases are not directly related to the artist himself.
            # It happens that if an artist has some feature songs on an album
            # for a different artist, it will be returned to the artist in cause
            # as well, so that this function checks that, and returns only feature
            # songs if it's the case.
            tracks = get_featuring_songs(sp_client, artist, detailed_album)
            processed_albums.extend(tracks)
        else:
            processed_albums.append(detailed_album)

    new_inserts = sync_with_db(processed_albums, dry_run)
    return new_inserts

def get_new_releases(sp_client: Spotify, dry_run: bool = False) -> None:
    """update artists with released albums"""
    for artist in Artist.select():
        update_artist_albums(sp_client, artist, dry_run)
