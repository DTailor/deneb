# flake8: noqa
from unittest.mock import MagicMock

from deneb.user_update import (
    extract_lost_follows_artists,
    extract_new_follows_objects,
    fetch_artists,
    check_follows,
)
from tests.unit.fixtures.mocks import sp_following
import pytest
from aiomock import AIOMock
from deneb.db import Artist


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


class TestCheckFollows:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "contains_follow",
        [
            [True, True, True],
            [True, True, False],
            [False, True, False],
            [True, False, True],
        ],
    )
    async def test_lost_artists(self, contains_follow):
        sp = AIOMock()
        # mock the response from "me/following/contains"
        sp.client._get.async_return_value = contains_follow
        artists = [
            Artist(name="test-artist1", spotify_id="test-id1"),
            Artist(name="test-artist2", spotify_id="test-id2"),
            Artist(name="test-artist3", spotify_id="test-id3"),
        ]

        lost_follows = await check_follows(sp, artists)

        # if contains, list must be empty else the artist
        assert len([a for a in contains_follow if a == False]) == len(lost_follows)
