# flake8: noqa
from unittest import mock

import pytest
from aiomock import AIOMock

from deneb.db import Artist
from deneb.workers.artist_sync import fetch_albums, get_featuring_songs
from tests.unit.common import _mocked_call
from tests.unit.fixtures.mocks import artist_db, get_album, get_track


class TestFetchAlbums:
    @pytest.mark.asyncio
    async def test_fetches_albums(self, artist_db):
        sp = AIOMock()
        sp.client.artist_albums.async_side_effect = [
            {"items": [get_album("1"), get_album("2")], "next": False}
        ]
        results = await fetch_albums(sp, artist_db)

        assert len(results) == 2
        sp.client.artist_albums.assert_called_once_with(
            artist_db.spotify_id, album_type="album,single,appears_on", limit=50
        )


class TestGetFeaturingSongs:
    @pytest.mark.asyncio
    async def test_fetches_featuring_songs(self):
        sp = AIOMock()
        album = get_album(name="1")
        sp.client.album_tracks.async_side_effect = [
            {
                "items": [
                    get_track("1", artist_name="1"),
                    get_track("2", artist_name="1"),
                ],
                "next": False,
            }
        ]
        artist = Artist(name="1", spotify_id=1)
        results = await get_featuring_songs(sp, artist, album)

        assert len(results) == 2
        sp.client.album_tracks.assert_called_once_with(
            album_id=artist.spotify_id, limit=50
        )

        for key in ["release_date", "release_date_precision"]:
            for item in results:
                assert key in item.keys()
