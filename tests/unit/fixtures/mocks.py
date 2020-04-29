import json
import os
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from aiomock import AIOMock


@pytest.fixture
def playlist() -> dict:
    playlist_path = os.path.join(os.path.dirname(__file__), "examples", "playlist.json")
    with open(playlist_path, "r") as f:
        playlist_data = f.read()
    return json.loads(playlist_data)


def get_track(name: str = "default-track", artist_name: str = "default-artist") -> dict:
    track_path = os.path.join(os.path.dirname(__file__), "examples", "track.json")
    with open(track_path, "r") as f:
        track_data = f.read()
    track_data = track_data.replace("TRACK_ID", name.lower()).replace(
        "ARTIST_ID", artist_name.lower()
    )
    return json.loads(track_data)


@pytest.fixture
def track() -> dict:
    return get_track()


def get_artist(name: str = "default-artist") -> dict:
    artist_path = os.path.join(os.path.dirname(__file__), "examples", "artist.json")
    with open(artist_path, "r") as f:
        artist_data = f.read()
    artist_data = artist_data.replace("TESTID", name.lower())
    artist_data = artist_data.replace("TEST_ID", name.capitalize())
    return json.loads(artist_data)


def get_album(name: str = "default-album") -> dict:
    album_path = os.path.join(os.path.dirname(__file__), "examples", "album.json")
    with open(album_path, "r") as f:
        album_data = f.read()
    album_data = (
        album_data.replace("TESTID", name.lower())
        .replace("TEST_ID", name.capitalize())
        .replace("DATE_FIELD", datetime.now().strftime("%Y-%m-%d"))
    )
    return json.loads(album_data)


@pytest.fixture
def artist() -> dict:
    return get_artist()


@pytest.fixture
def album() -> dict:
    return get_album()


@pytest.fixture
def album_db() -> MagicMock:
    album = MagicMock()
    album.name = "Test Album"

    # artist = MagicMock()
    # artist.name = "Test Artist"

    # album.artists = [artist]

    # album.human_name = MagicMock()
    # album.human_name.return_value = "Test Artist - Test Album"

    return album


@pytest.fixture
def artist_db() -> MagicMock:
    artist = MagicMock()
    return artist


@pytest.fixture
def sp_following() -> AIOMock:
    sp = AIOMock()

    # config returned artists
    sp.client.current_user_followed_artists = AIOMock()
    sp.client.current_user_followed_artists.async_return_value = {
        "artists": {"items": [get_artist("1")], "next": True}
    }

    sp.client.next = AIOMock()
    sp.client.next.async_return_value = {
        "artists": {"items": [get_artist("2")], "next": False}
    }
    return sp
