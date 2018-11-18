"""Spotify connection handling"""

import os
import weakref

import spotipy
from spotipy import util
from spotipy.client import SpotifyException
from typing import Tuple
from logger import get_logger

# check spotify environ keys are set
assert os.environ['SPOTIPY_CLIENT_ID']
assert os.environ['SPOTIPY_CLIENT_SECRET']
assert os.environ['SPOTIPY_REDIRECT_URI']

_SPOTI_CACHE = weakref.WeakValueDictionary()    # type: weakref.WeakValueDictionary
_SP_SCOPE = ' '.join([
    'user-follow-read',
    'user-read-private',
    'playlist-modify-public',
    'playlist-modify-private'
    ]
)
_LOGGER = get_logger(__name__)


def fetch_token(username: str) -> str:
    """gen an access token"""
    token = util.prompt_for_user_token(
        username=username,
        scope=_SP_SCOPE,
        client_id=os.environ['SPOTIPY_CLIENT_ID'],
        client_secret=os.environ['SPOTIPY_CLIENT_SECRET'],
        redirect_uri=os.environ['SPOTIPY_REDIRECT_URI']
    )
    return token


class Spotter:
    def __init__(self, username: str, client: spotipy.Spotify) -> None:
        self.username = username
        self.client = client


def get_sp_client(username: str, token: str = None)-> Tuple[spotipy.Spotify, str]:
    """returns new sp client plus the token for it"""
    if token is None:
        token = fetch_token(username)

    if token in _SPOTI_CACHE:
        sp = _SPOTI_CACHE[token]
    else:
        sp_client = spotipy.Spotify(auth=token)
        sp = Spotter(username, sp_client)

    try:
        # check client stil good
        sp.client.current_user()
    except SpotifyException as exc:
        if token in _SPOTI_CACHE:
            del _SPOTI_CACHE[token]
        _LOGGER.warning(f"bad token for <{username}>: {exc}")
        # token may expire, ask for new
        token = fetch_token(username)
        sp_client = spotipy.Spotify(auth=token)
        sp = Spotter(username, sp_client)
        _SPOTI_CACHE[token] = sp

    return sp, token
