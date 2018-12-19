import pytest
import os
import json


@pytest.fixture
def playlist() -> dict:
    playlist_path = os.path.join(os.path.dirname(__file__), "examples", "playlist.json")
    with open(playlist_path, 'r') as f:
        playlist_data = f.read()
    return json.loads(playlist_data)
