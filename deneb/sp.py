"""Spotify connection handling"""
import asyncio
import json
import random
import time
from contextlib import asynccontextmanager
from typing import Dict, List

import aiohttp
from spotipy.client import Spotify, SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from deneb.db import User
from deneb.logger import get_logger
from deneb.structs import SpotifyKeys

_LOGGER = get_logger(__name__)


@asynccontextmanager
async def spotify_client(credentials: SpotifyKeys, user: User):
    """
    context manager to aquire spotify client
    """
    token_info = json.loads(user.spotify_token)
    sp = await get_client(credentials, token_info)
    try:
        yield sp
    finally:
        await user.async_data(sp)
        await sp.client.session.close()


class Spotter:
    def __init__(self, client: Spotify, userdata: dict) -> None:
        self.client = client
        self.userdata = userdata


class AsyncSpotify(Spotify):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        conn = aiohttp.TCPConnector(limit=10)
        self.session = aiohttp.ClientSession(connector=conn)

    async def _get(self, url, args=None, payload=None, **kwargs):
        result = await self._async_get(url, args=None, payload=None, **kwargs)
        return result

    async def current_user(self):
        """ Get detailed profile information about the current user.
            An alias for the 'current_user' method.
        """
        return await self.me()

    async def user_playlist(self, user, playlist_id=None, fields=None):
        """ Gets playlist of a user
            Parameters:
                - user - the id of the user
                - playlist_id - the id of the playlist
                - fields - which fields to return
        """
        if playlist_id is None:
            return await self._get("users/%s/starred" % (user), fields=fields)
        plid = self._get_id("playlist", playlist_id)
        return await self._get("users/%s/playlists/%s" % (user, plid), fields=fields)

    async def __async_internal_call(self, method, url, payload, params):
        # remove all none valued keys
        # aiohttp fails to encode those
        params = {key: val for key, val in params.items() if val}
        args = {"params": params}

        if not url.startswith("http"):
            url = self.prefix + url
        headers = self._auth_headers()
        headers["Content-Type"] = "application/json"

        if payload:
            args["data"] = json.dumps(payload)

        async with self.session.request(
            method, url, headers=headers, timeout=60, **args
        ) as res:
            try:
                res.text = await res.text()
                res.json = json.loads(res.text)
                res.raise_for_status()
            except aiohttp.ClientResponseError:
                if res.text and len(res.text) > 0 and res.text != "null":
                    raise SpotifyException(
                        res.status,
                        -1,
                        "%s:\n %s" % (res.url, res.json["error"]["message"]),
                        headers=res.headers,
                    )
                else:
                    raise SpotifyException(
                        res.status,
                        -1,
                        "%s:\n %s" % (res.url, "error"),
                        headers=res.headers,
                    )
            if res.text and len(res.text) > 0 and res.text != "null":
                results = res.json
                return results
            else:
                return None

    async def _async_get(self, url, args=None, payload=None, **kwargs):
        if args:
            kwargs.update(args)
        retries = self.max_get_retries
        delay = 2
        while retries > 0:
            try:
                return await self.__async_internal_call("GET", url, payload, kwargs)
            except SpotifyException as e:
                retries -= 1
                status = e.http_status

                if status == 401:
                    # unauthorized call; will be handled by refresh token
                    raise

                # 429 means we hit a rate limit, backoff
                if status == 429 or (status >= 500 and status < 600):
                    if retries < 0:
                        raise
                    else:
                        sleep_seconds = int(e.headers.get("Retry-After", delay)) + 1
                        await asyncio.sleep(sleep_seconds)
                        delay += 1
                else:
                    _LOGGER.exception(f"bad request {url}: {e}")
                    raise
            except (json.JSONDecodeError, asyncio.TimeoutError):
                retries -= 1
                if retries >= 0:
                    sleep_seconds = delay + 1
                    await asyncio.sleep(sleep_seconds)
                    delay += 1
                else:
                    raise


async def get_client(credentials: SpotifyKeys, token_info: dict) -> Spotter:
    """returns a spotter obj with spotipy client"""
    sp_oauth = SpotifyOAuth(
        credentials.client_id, credentials.client_secret, credentials.client_uri
    )
    client_credentials = SpotifyClientCredentials(
        credentials.client_id, credentials.client_secret
    )

    if "expires_at" not in token_info:
        token_info["expires_at"] = int(time.time()) + 1000
    client_credentials.token_info = token_info
    client = AsyncSpotify(client_credentials_manager=client_credentials)

    try:
        current_user = await client.current_user()
    except Exception as exc:
        _LOGGER.info(f"got {exc} of type {type(exc)}")

        # need new client, close old client session
        await client.session.close()
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        client_credentials.token_info = token_info
        client = AsyncSpotify(client_credentials_manager=client_credentials)
        current_user = await client.current_user()
        _LOGGER.info(f"aquired new token for {current_user['id']}")

    sp = Spotter(client, current_user)
    return sp


class SpotifyStats:
    def __init__(self, fb_id: str, playlist: dict, added_items: Dict[str, List]):
        self.fb_id = fb_id
        self.playlist = playlist
        self.added_singles = added_items["singles"]
        self.added_albums = added_items["albums"]
        self.added_tracks = added_items["tracks"]

    @staticmethod
    def humanize_track(track: Dict) -> str:
        artists = ", ".join(a["name"] for a in track["artists"])
        return f"{artists} - {track['name']}"

    def describe(self) -> str:
        didnt_add_responses = [
            "Uhh, sorry, no releases today for you.",
            "Didn't find anything new today",
            "Sad day, no new music",
            "No adds, you should follow more artists",
        ]
        if self.added_albums or self.added_tracks or self.added_singles:
            return_msg = f"Playlist: {self.playlist['name']}\n\n"

            if self.added_singles:
                return_msg = f"{return_msg}-== Singles ==-\n"
                for album in self.added_singles:
                    tmp_msg = f"{self.humanize_track(album.parent)}\n"
                    for track in album.tracks:
                        tmp_msg = f"{tmp_msg}   {track['name']}\n"
                    return_msg = f"{return_msg}{tmp_msg}\n"

            if self.added_albums:
                return_msg = f"{return_msg}-== Albums ==-\n"
                for album in self.added_albums:
                    tmp_msg = f"{self.humanize_track(album.parent)}\n"
                    for track in album.tracks:
                        tmp_msg = f"{tmp_msg}   {track['name']}\n"
                    return_msg = f"{return_msg}{tmp_msg}\n"

            if self.added_tracks:
                return_msg = f"{return_msg}-==Tracks from albums ==-\n"
                for album in self.added_tracks:
                    tmp_msg = f"{self.humanize_track(album.parent)}\n"

                    for track in album.tracks:
                        tmp_msg = f"{tmp_msg}   {self.humanize_track(track)}\n"
                    return_msg = f"{return_msg}{tmp_msg}\n"

            return_msg = (
                f"{return_msg}Link: {self.playlist['external_urls']['spotify']}"
            )
            return return_msg

        return random.choice(didnt_add_responses)
