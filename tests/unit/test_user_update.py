# flake8: noqa
from unittest.mock import MagicMock

from deneb.user_update import (
    extract_lost_follows_artists,
    extract_new_follows_objects,
    fetch_artists,
)
from tests.unit.fixtures.mocks import sp_following
import pytest


class TestFetchArtist:
    # implying only 2 artists come at this point

    @pytest.mark.asyncio
    async def test_fetch_artist_ok(self, sp_following):
        artists = await fetch_artists(sp_following)
        assert len(artists) == 2


class TestExtractNewFollowsObjects:
    def test_one_exclude(self):
        followed_artists = [{"id": "stay"}, {"id": "stay2"}, {"id": "leave"}]
        following_ids = ["leave"]
        result = extract_new_follows_objects(followed_artists, following_ids)
        assert len(result) == 2

    def test_no_exclude(self):
        followed_artists = [{"id": "stay"}, {"id": "stay2"}, {"id": "leave"}]
        following_ids = []
        result = extract_new_follows_objects(followed_artists, following_ids)
        assert result == followed_artists


class TestExtractLostFollowsArtists:
    def test_one_lost(self):
        followed_artists = [{"id": "stay"}, {"id": "stay2"}]
        current_following = [
            MagicMock(spotify_id="stay"),
            MagicMock(spotify_id="stay2"),
            MagicMock(spotify_id="leave"),
        ]
        lost = extract_lost_follows_artists(followed_artists, current_following)
        assert len(lost) == 1
        assert lost[0].spotify_id == "leave"
