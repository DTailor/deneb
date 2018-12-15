"""Spotify connection handling"""

import json
from typing import Tuple

from spotipy.client import Spotify
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from logger import get_logger

_LOGGER = get_logger(__name__)


class Spotter:
    def __init__(self, client: Spotify, userdata: dict) -> None:
        self.client = client
        self.userdata = userdata


def get_client(
    client_id: str,
    client_secret: str,
    client_uri: str,
    token_info: dict
) -> Tuple[Spotify, dict]:
    """returns a spotter obj with spotipy client"""
    sp_oauth = SpotifyOAuth(client_id, client_secret, client_uri)

    if "expires_at" not in token_info.keys():
        token_info = sp_oauth._add_custom_values_to_token_info(token_info)

    if sp_oauth._is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info)

    client_credentials = SpotifyClientCredentials(
        client_id,
        client_secret
    )
    client_credentials.token_info = token_info
    client = Spotify(client_credentials_manager=client_credentials)
    sp = Spotter(client, client.me())
    return sp, token_info
