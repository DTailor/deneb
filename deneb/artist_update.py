"""Module to handle artist related updates"""

from spotipy import Spotify

from db import Album, Artist  # pylint: disable=import-error


def fetch_all(sp_client: Spotify, data: dict) -> list:
    """iterates till gets all the albums"""
    contents = []
    while data:
        contents.extend(data["items"])
        data = sp_client.next(data)
    return contents


def fetch_albums(
        sp_client: Spotify, artist: Artist, retry: bool = False
) -> list(Album):
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


def update_artist_albums(sp_client: Spotify, artist: Artist) -> None:
    """update artist albums"""
    albums = fetch_albums(sp_client, artist)
    for album in albums:
        print('{}: {}'.format(artist, album))


def get_new_releases(sp_client: Spotify) -> None:
    """update artists with released albums"""
    for artist in Artist.select():
        update_artist_albums(sp_client, artist)
