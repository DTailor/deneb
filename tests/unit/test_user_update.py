# flake8: noqa
from unittest import mock

import pytest
from aiomock import AIOMock

from deneb.db import Artist
from deneb.user_update import (
    check_follows, extract_lost_follows_artists, extract_new_follows_objects,
    fetch_artists, fetch_user_followed_artists
)
from tests.unit.common import _mocked_call
from tests.unit.fixtures.mocks import get_artist, sp_following


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
            mock.MagicMock(spotify_id="stay"),
            mock.MagicMock(spotify_id="stay2"),
            mock.MagicMock(spotify_id="leave"),
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


class TestFetchUserFollowedArtists:
    @pytest.mark.asyncio
    async def test_no_follows(self):
        user = AIOMock()
        user.artists.filter.async_return_value = []
        sp = AIOMock()

        with mock.patch(
            "deneb.user_update.fetch_artists", new=AIOMock()
        ) as mock_fetch_artists:
            mock_fetch_artists.async_return_value = []
            new, lost = await fetch_user_followed_artists(user, sp, False)
            mock_fetch_artists.assert_called_once_with(sp)

    @pytest.mark.asyncio
    async def test_one_add_follows(self):
        user = AIOMock()
        user.artists.filter = _mocked_call([])
        user.artists.add = _mocked_call()
        sp = AIOMock()

        artist = get_artist()
        with mock.patch(
            "deneb.user_update.fetch_artists", new=AIOMock()
        ) as mock_fetch_artists:
            with mock.patch("deneb.user_update.Artist", new=AIOMock()) as mock_artist:
                # mock data received from spotify
                mock_fetch_artists.async_return_value = [artist]

                # mock model querying
                db_artist = AIOMock()
                mock_artist.filter = _mocked_call([])
                mock_artist.create = _mocked_call([db_artist])

                new, lost = await fetch_user_followed_artists(user, sp, False)

                mock_fetch_artists.assert_called_once_with(sp)
                assert user.artists.filter.call_count == 2
                mock_artist.filter.assert_called_once_with(spotify_id=artist["id"])
                mock_artist.create.assert_called_once_with(
                    name=artist["name"], spotify_id=artist["id"]
                )
                user.artists.add.assert_called_once_with([db_artist])

    @pytest.mark.asyncio
    async def test_one_lost_follows(self):
        db_artist = AIOMock()
        user = AIOMock()
        user.artists.filter = _mocked_call([db_artist])
        user.artists.remove = _mocked_call()
        sp = AIOMock()

        with mock.patch(
            "deneb.user_update.fetch_artists", new=AIOMock()
        ) as mock_fetch_artists:
            with mock.patch("deneb.user_update.Artist", new=AIOMock()) as mock_artist:
                with mock.patch(
                    "deneb.user_update.check_follows", new=AIOMock()
                ) as mock_check_follows:
                    # mock data received from spotify
                    mock_check_follows.async_return_value = [db_artist]
                    mock_fetch_artists.async_return_value = []

                    new, lost = await fetch_user_followed_artists(user, sp, False)

                    mock_fetch_artists.assert_called_once_with(sp)
                    assert user.artists.filter.call_count == 2
                    mock_check_follows.assert_called_once_with(sp, [db_artist])
                    user.artists.remove.assert_called_once_with(db_artist)
