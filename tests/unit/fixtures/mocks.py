import json
import os

import pytest
from mock import MagicMock


@pytest.fixture
def playlist() -> dict:
    playlist_path = os.path.join(os.path.dirname(__file__), "examples", "playlist.json")
    with open(playlist_path, 'r') as f:
        playlist_data = f.read()
    return json.loads(playlist_data)


def get_track() -> dict:
    track_path = os.path.join(os.path.dirname(__file__), "examples", "track.json")
    with open(track_path, 'r') as f:
        track_data = f.read()
    return json.loads(track_data)


@pytest.fixture
def track() -> dict:
    return get_track()


@pytest.fixture
def album_db():
    album = MagicMock()
    album.name = 'Test Album'

    artist = MagicMock()
    artist.name = 'Test Artist'

    album.artists = MagicMock()
    album.artists.return_value = [artist]

    album.human_name = MagicMock()
    album.human_name.return_value = 'Test Artist - Test Album'

    return album
