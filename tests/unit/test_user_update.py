# flake8: noqa
from deneb.user_update import fetch_artists
from tests.unit.fixtures.mocks import sp_following


class TestFetchArtist:
    # implying only 2 artists come at this point

    def test_fetch_artist_ok(self, sp_following):
        artists = fetch_artists(sp_following)
        assert len(artists) == 2
