# flake8: noqa
from deneb.structs import SpotifyStats
from tests.unit.fixtures.mocks import playlist


class TestSpotifyStats:

    def test_one_added_track(self, playlist):
        one_track = ["one-track-lol"]

        ss = SpotifyStats('test_user', playlist, one_track)

        expected_string = "I added 1 track to Test Playlist"
        assert ss.describe() == expected_string

    def test_more_added_tracks(self, playlist):
        more_tracks = ["one", "two"]

        ss = SpotifyStats("test_user", playlist, more_tracks)

        expected_string = "I added 2 tracks to Test Playlist"
        assert ss.describe() == expected_string

    def test_empty_added_tracks(self, playlist):
        valid_responses = [
            "Uhh, sorry, no releases today for you.",
            "Didn't find anything new today",
            "Sad day, no new music",
            "No adds, you should follow more artists",
        ]

        ss = SpotifyStats("test_user", playlist, [])

        assert ss.describe() in valid_responses
