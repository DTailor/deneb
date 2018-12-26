# flake8: noqa
from deneb.structs import SpotifyStats, AlbumTracks
from tests.unit.fixtures.mocks import playlist, track, album_db


class TestSpotifyStats:
    def test_humanize_track(self, track):
        noalbum_tracks = AlbumTracks(parent=None, tracks=[track])

        assert SpotifyStats.humanize_track(noalbum_tracks) == "Test Track - Test Track"

    def test_describe_added_album(self, playlist, album_db, track):
        album_tracks = AlbumTracks(parent=album_db, tracks=[track, track, track])
        stats = SpotifyStats(
            "test-id", playlist, {"tracks": [], "albums": [album_tracks]}
        )

        expected = [
            "Test Playlist",
            "Albums:",
            "- [Test Artist - Test Album]",
            "   * Test Track",
            "   * Test Track",
            "   * Test Track",
            "",
        ]

        output = stats.describe()

        for line1, line2 in zip(output.splitlines(), expected):
            assert line1 == line2

    def test_describe_added_track(self, playlist, track):
        album_tracks = AlbumTracks(parent=None, tracks=[track])
        stats = SpotifyStats(
            "test-id", playlist, {"tracks": [album_tracks], "albums": []}
        )

        expected = ["Test Playlist", "Tracks:", " * Test Track - Test Track"]

        output = stats.describe()

        for line1, line2 in zip(output.splitlines(), expected):
            assert line1 == line2

    def test_describe_added_tracks_and_albums(self, playlist, album_db, track):
        album_tracks = AlbumTracks(parent=album_db, tracks=[track, track, track])
        just_tracks = AlbumTracks(parent=None, tracks=[track, track, track])
        stats = SpotifyStats(
            "test-id", playlist, {"tracks": [just_tracks], "albums": [album_tracks]}
        )

        expected = [
            "Test Playlist",
            "Albums:",
            "- [Test Artist - Test Album]",
            "   * Test Track",
            "   * Test Track",
            "   * Test Track",
            "",
            "Tracks:",
            " * Test Track - Test Track",
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
