"""Spotify connection handling"""

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
    refresh_token: str
) -> Tuple[Spotify, dict]:
    """returns a spotter obj with spotipy client"""
    sp_oauth = SpotifyOAuth(client_id, client_secret, client_uri)
    new_token_info = sp_oauth.refresh_access_token(refresh_token)

    client_credentials = SpotifyClientCredentials(
        client_id,
        client_secret
    )
    client_credentials.token_info = new_token_info
    client = Spotify(client_credentials_manager=client_credentials)
    sp = Spotter(client, client.me())
    return sp, new_token_info
