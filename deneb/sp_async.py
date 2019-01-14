"""Spotify connection handling"""
import json
import random
import time
from contextlib import asynccontextmanager
from typing import Dict, List

from spotipy.client import Spotify
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from deneb.db_async import User
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


class Spotter:
    def __init__(self, client: Spotify, userdata: dict) -> None:
        self.client = client
        self.userdata = userdata


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
    client = Spotify(client_credentials_manager=client_credentials)

    try:
        current_user = client.current_user()
    except Exception:
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        client_credentials.token_info = token_info
        client = Spotify(client_credentials_manager=client_credentials)
        current_user = client.current_user()
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
