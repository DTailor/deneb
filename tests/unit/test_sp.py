# flake8: noqa
from deneb.sp import SpotifyStats, spotify_client, get_client, Spotter
from deneb.structs import AlbumTracks, SpotifyKeys
from tests.unit.fixtures.mocks import album, playlist, track
from unittest.mock import MagicMock, patch


class TestSpotifyClient:
    def test_context_flow(self):
        user = MagicMock()
        user.spotify_token = "{}"
        sp_client = None
        with patch("deneb.sp.get_client") as mock_get_client:
            with spotify_client(credentials=None, user=user) as sp:
                sp_client = sp
            mock_get_client.assert_called_once()

        user.sync_data.assert_called_once_with(sp_client)


class TestSpotter:
    def test_spotter_object(self):
        obj = Spotter("client", "userdata")
        assert obj.client == "client"
        assert obj.userdata == "userdata"


class TestGetClient:
    def test_get_client(self):
        keys = SpotifyKeys("", "", "")
        token_info = dict()
        with patch("deneb.sp.Spotify") as mocked_spotify:
            sp = get_client(keys, token_info)

            # initialized spotify client
            mocked_spotify.assert_called_once()

            # called current user method
            sp.client.current_user.assert_called_once()

    @patch("deneb.sp._LOGGER")
    @patch("deneb.sp.SpotifyOAuth")
    @patch("deneb.sp.Spotify.current_user", side_effect=[Exception(), {"id": "test"}])
    def test_get_client_exception(self, current_user, oauth, logger):
        keys = SpotifyKeys("", "", "")
        token_info = {"refresh_token": ""}

        sp = get_client(keys, token_info)

        oauth.assert_called_once()
        assert current_user.call_count == 2
        logger.info.assert_called_once()


class TestSpotifyStats:
    def test_humanize_track(self, track):
        noalbum_tracks = AlbumTracks(parent=None, tracks=[track])

        assert (
            SpotifyStats.humanize_track(noalbum_tracks.tracks[0])
            == "Test Artist - Test Track"
        )

    def test_describe_added_album(self, playlist, album, track):
        album_tracks = AlbumTracks(parent=album, tracks=[track, track, track])
        stats = SpotifyStats(
            "test-id", playlist, {"tracks": [], "albums": [album_tracks]}
        )

        expected = [
            "Playlist: Test Playlist",
            "",
            "-== Albums ==-",
            "Test Artist - Test Album",
            "   * Test Track",
            "   * Test Track",
            "   * Test Track",
            "",
            "Link: https://open.spotify.com/playlist/test_playlist",
        ]
        output = stats.describe()

        for line1, line2 in zip(output.splitlines(), expected):
            assert line1 == line2

    def test_describe_added_track(self, album, playlist, track):
        album_tracks = AlbumTracks(parent=album, tracks=[track])
        stats = SpotifyStats(
            "test-id", playlist, {"tracks": [album_tracks], "albums": []}
        )

        expected = [
            "Playlist: Test Playlist",
            "",
            "-==Tracks from albums ==-",
            "Test Artist - Test Album",
            "   Test Artist - Test Track",
            "",
            "Link: https://open.spotify.com/playlist/test_playlist",
        ]

        output = stats.describe()

        for line1, line2 in zip(output.splitlines(), expected):
            assert line1 == line2

    def test_describe_added_tracks_and_albums(self, playlist, album, track):
        album_tracks = AlbumTracks(parent=album, tracks=[track, track, track])
        stats = SpotifyStats(
            "test-id", playlist, {"tracks": [album_tracks], "albums": [album_tracks]}
        )

        expected = [
            "Playlist: Test Playlist",
            "",
            "-== Albums ==-",
            "Test Artist - Test Album",
            "   * Test Track",
            "   * Test Track",
            "   * Test Track",
            "",
            "-==Tracks from albums ==-",
            "Test Artist - Test Album",
            "   Test Artist - Test Track",
            "   Test Artist - Test Track",
            "   Test Artist - Test Track",
            "",
            "Link: https://open.spotify.com/playlist/test_playlist",
        ]

        output = stats.describe()

        for line1, line2 in zip(output.splitlines(), expected):
            assert line1 == line2

    def test_describe_nothing_added(self, playlist):
        valid_responses = [
            "Uhh, sorry, no releases today for you.",
            "Didn't find anything new today",
            "Sad day, no new music",
            "No adds, you should follow more artists",
        ]

        ss = SpotifyStats("test-id", playlist, {"albums": [], "tracks": []})

        assert ss.describe() in valid_responses
