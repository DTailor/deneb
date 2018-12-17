"""Spotify connection handling"""
import time

from spotipy.client import Spotify
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from deneb.logger import get_logger

_LOGGER = get_logger(__name__)


class Spotter:
    def __init__(self, client: Spotify, userdata: dict) -> None:
        self.client = client
        self.userdata = userdata


def get_client(
    client_id: str, client_secret: str, client_uri: str, token_info: dict
) -> Spotter:
    """returns a spotter obj with spotipy client"""
    sp_oauth = SpotifyOAuth(client_id, client_secret, client_uri)
    client_credentials = SpotifyClientCredentials(client_id, client_secret)

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
