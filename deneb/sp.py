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
from deneb.logger import get_logger, push_sentry_error
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
        try:
            await user.async_data(sp)
        except ValueError as exc:
            _LOGGER.exception(f"{sp.userdata['id']} on sync user with db")
            push_sentry_error(exc, sp.userdata["id"], sp.userdata["display_name"])

        await sp.client.session.close()


class Spotter:
    def __init__(self, client: Spotify, userdata: dict) -> None:
        self.client = client
        self.userdata = userdata


class AsyncSpotify(Spotify):  # pragma: no cover
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        conn = aiohttp.TCPConnector(limit=10)
        self.session = aiohttp.ClientSession(connector=conn)

    async def current_user(self):
        """ Get detailed profile information about the current user.
            An alias for the 'current_user' method.
        """
        return await self.me()

    async def current_user_saved_tracks(self, limit=20, offset=0):
        """ Gets a list of the tracks saved in the current authorized user's
            "Your Music" library

            Parameters:
                - limit - the number of tracks to return
                - offset - the index of the first track to return

        """
        return await self._get("me/tracks", limit=limit, offset=offset)

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

    async def _get(self, url, args=None, payload=None, **kwargs):
        result = await self._async_request(
            "GET", url, args=None, payload=None, **kwargs
        )
        return result

    async def _post(self, url, args=None, payload=None, **kwargs):
        result = await self._async_request("POST", url, args, payload, **kwargs)
        return result

    async def _async_request(self, method, url, args=None, payload=None, **kwargs):
        if args:
            kwargs.update(args)
        retries = self.max_get_retries
        delay = 2
        while retries > 0:
            try:
                return await self.__async_internal_call(method, url, payload, kwargs)
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

    async def __async_internal_call(self, method, url, payload, params):
        # remove all none valued keys
        # aiohttp fails to encode those
        params = {key: val for key, val in params.items() if val is not None}
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
    except SpotifyException:
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
        self.added_singles = added_items.get("singles", [])
        self.added_albums = added_items.get("albums", [])
        self.added_tracks = added_items.get("tracks", [])

    @staticmethod
    def humanize_track(track: Dict) -> str:
        artists = ", ".join(a["name"] for a in track["artists"])
        return f"{artists} - {track['name']}"

    def has_new_tracks(self) -> int:
        everything = self.added_albums + self.added_tracks + self.added_singles
        return len(everything)

    def format_tracklist(self, category: str, items: List) -> str:
        if not items:
            return ""

        return_msg = f"-== {category} ==-\n"
        for item in items:
            tmp_msg = f"{self.humanize_track(item.parent)}"
            return_msg = f"{return_msg}{tmp_msg}\n"

        return f"{return_msg}\n"

    def describe(self, brief: bool = False) -> str:
        if brief:
            return (
                f"s: {len(self.added_singles)} "
                f"a: {len(self.added_albums)} "
                f"t: {len(self.added_tracks)}"
            )

        fallback_responses = [
            "Uhh, sorry, no new tracks.",
            "Nothing new",
            "Sad day, no new music",
            "No adds, you should follow more artists",
        ]
        if not self.has_new_tracks():
            return random.choice(fallback_responses)

        return_msg = f"Playlist: {self.playlist['name']}\n\n"

        for category, items in (
            ("Singles", self.added_singles),
            ("Albums", self.added_albums),
            ("Tracks", self.added_tracks),
        ):
            if items:
                tracklist = self.format_tracklist(category, items)
                return_msg = f"{return_msg}{tracklist}"

        return_msg = f"{return_msg}Link: {self.playlist['external_urls']['spotify']}"
        return return_msg


class SpotifyYearlyStats(SpotifyStats):
    @staticmethod
    def humanize_track(track: Dict) -> str:
        artists = ", ".join(a["name"] for a in track["artists"])
        return f"{artists} - {track['name']}"

    def format_tracklist(self, category: str, items: List) -> str:
        if not items:
            return ""

        return_msg = f"-== {category} ==-\n"
        for item in items:
            tmp_msg = f"{self.humanize_track(item)}"
            return_msg = f"{return_msg}{tmp_msg}\n"

        return f"{return_msg}\n"
