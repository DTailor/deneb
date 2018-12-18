"""Spotify connection handling"""
import json
import time
from contextlib import contextmanager
from typing import Generator

from spotipy.client import Spotify
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from deneb.db import User
from deneb.logger import get_logger
from deneb.structs import SpotifyKeys

_LOGGER = get_logger(__name__)


@contextmanager
def spotify_client(credentials: SpotifyKeys, user: User) -> Generator:
    """
    context manager to aquire spotify client
    """
    token_info = json.loads(user.spotify_token)
    sp = get_client(credentials, token_info)
    try:
        yield sp
    finally:
        user.sync_data(sp)


class Spotter:
    def __init__(self, client: Spotify, userdata: dict) -> None:
        self.client = client
        self.userdata = userdata


def get_client(
    credentials: SpotifyKeys, token_info: dict
) -> Spotter:
    """returns a spotter obj with spotipy client"""
    sp_oauth = SpotifyOAuth(
        credentials.client_id, credentials.client_secret, credentials.client_uri)
    client_credentials = SpotifyClientCredentials(
        credentials.client_id, credentials.client_secret)

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
