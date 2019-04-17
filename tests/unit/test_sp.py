# flake8: noqa
from unittest.mock import MagicMock, patch

import pytest
from aiomock import AIOMock
from spotipy import SpotifyException

from deneb.sp import SpotifyStats, Spotter, get_client, spotify_client
from deneb.structs import AlbumTracks, SpotifyKeys
from tests.unit.common import _mocked_call
from tests.unit.fixtures.mocks import album, playlist, track


class TestSpotifyClient:
    @pytest.mark.asyncio
    async def test_context_flow(self):
        user = AIOMock()
        user.async_data = _mocked_call()
        user.spotify_token = "{}"
        sp_client = None
        with patch("deneb.sp.get_client", new=AIOMock()) as mock_get_client:
            mocked_sp = AIOMock()
            mocked_sp.client.session.close = _mocked_call()
            mock_get_client.async_return_value = mocked_sp

            async with spotify_client(credentials=None, user=user) as sp:
                sp_client = sp
            mock_get_client.assert_called_once()

        user.async_data.assert_called_once_with(sp_client)
        sp_client.client.session.close.assert_called_once()


class TestSpotter:
    def test_spotter_object(self):
        obj = Spotter("client", "userdata")
        assert obj.client == "client"
        assert obj.userdata == "userdata"


class TestGetClient:
    @pytest.mark.asyncio
    async def test_get_client(self):
        keys = SpotifyKeys("", "", "")
        token_info = dict()
        with patch("deneb.sp.AsyncSpotify") as mocked_spotify:
            mocked_sp = AIOMock()
            mocked_sp.current_user.async_return_value = mocked_sp
            mocked_spotify.return_value = mocked_sp
            sp = await get_client(keys, token_info)

            # initialized spotify client
            mocked_spotify.assert_called_once()

            # called current user method
            sp.client.current_user.assert_called_once()

    @pytest.mark.asyncio
    @patch("deneb.sp._LOGGER")
    @patch("deneb.sp.SpotifyOAuth")
    @patch("deneb.sp.Spotify.current_user", side_effect=[Exception(), {"id": "test"}])
    async def test_get_client_exception(self, current_user, oauth, logger):
        keys = SpotifyKeys("", "", "")
        token_info = {"refresh_token": ""}

        with patch("deneb.sp.AsyncSpotify") as mocked_spotify:
            mocked_sp = AIOMock()
            mocked_sp.current_user.async_side_effect = [
                SpotifyException(http_status=401, code=401, msg="Unauthorized"),
                {"id": "test-user"},
            ]
            mocked_sp.session.close = _mocked_call()
            mocked_spotify.return_value = mocked_sp

            sp = await get_client(keys, token_info)

            # try and except
            assert mocked_spotify.call_count == 2
            assert sp.client.current_user.call_count == 2
            mocked_sp.session.close.assert_called_once()


class TestSpotifyStats:
    @pytest.mark.asyncio
    async def test_humanize_track(self, track):
        noalbum_tracks = AlbumTracks(parent=None, tracks=[track])

        assert (
            SpotifyStats.humanize_track(noalbum_tracks.tracks[0])
            == "Test Artist - Test Track"
        )

    @pytest.mark.asyncio
    async def test_describe_added_album(self, playlist, album, track):
        album_tracks = AlbumTracks(parent=album, tracks=[track, track, track])
        stats = SpotifyStats(
            "test-id", playlist, {"tracks": [], "albums": [album_tracks], "singles": []}
        )

        expected = [
            "Playlist: Test Playlist",
            "",
            "-== Albums ==-",
            "Test Artist - Test Album",
            "",
            "Link: https://open.spotify.com/playlist/test_playlist",
        ]
        output = stats.describe()

        for line1, line2 in zip(output.splitlines(), expected):
            assert line1 == line2

    @pytest.mark.asyncio
    async def test_describe_added_track(self, album, playlist, track):
        album_tracks = AlbumTracks(parent=album, tracks=[track])
        stats = SpotifyStats(
            "test-id", playlist, {"tracks": [album_tracks], "albums": [], "singles": []}
        )

        expected = [
            "Playlist: Test Playlist",
            "",
            "-== Featuring tracks from other albums ==-",
            "Test Artist - Test Album",
            "",
            "Link: https://open.spotify.com/playlist/test_playlist",
        ]

        output = stats.describe()

        for line1, line2 in zip(output.splitlines(), expected):
            assert line1 == line2

    @pytest.mark.asyncio
    async def test_describe_added_tracks_and_albums(self, playlist, album, track):
        album_tracks = AlbumTracks(parent=album, tracks=[track, track, track])
        stats = SpotifyStats(
            "test-id",
            playlist,
            {"tracks": [album_tracks], "albums": [album_tracks], "singles": []},
        )

        expected = [
            "Playlist: Test Playlist",
            "",
            "-== Albums ==-",
            "Test Artist - Test Album",
            "",
            "-== Featuring tracks from other albums ==-",
            "Test Artist - Test Album",
            "",
            "Link: https://open.spotify.com/playlist/test_playlist",
        ]

        output = stats.describe()

        for line1, line2 in zip(output.splitlines(), expected):
            assert line1 == line2

    @pytest.mark.asyncio
    async def test_describe_nothing_added(self, playlist):
        valid_responses = [
            "Uhh, sorry, no releases today for you.",
            "Didn't find anything new today",
            "Sad day, no new music",
            "No adds, you should follow more artists",
        ]

        ss = SpotifyStats(
            "test-id", playlist, {"albums": [], "tracks": [], "singles": []}
        )

        assert ss.describe() in valid_responses
