"""Spotify connection handling"""

import os
import weakref
from enum import Enum

import spotipy
from spotipy import util
from spotipy.client import SpotifyException

from logger import get_logger

# check spotify environ keys are set
assert os.environ['SPOTIPY_CLIENT_ID']
assert os.environ['SPOTIPY_CLIENT_SECRET']
assert os.environ['SPOTIPY_REDIRECT_URI']

_SPOTI_CACHE = weakref.WeakValueDictionary()

_LOGGER = get_logger(__name__)


def fetch_token(username):
    """gen an access token"""
    token = util.prompt_for_user_token(
        username=username,
        scope='user-follow-read user-read-private playlist-modify-public',
        client_id=os.environ['SPOTIPY_CLIENT_ID'],
        client_secret=os.environ['SPOTIPY_CLIENT_SECRET'],
        redirect_uri=os.environ['SPOTIPY_REDIRECT_URI']
    )
    return token


class Spotter:
    def __init__(self, username, client):
        self.username = username
        self.client = client


def get_sp_client(username, token=None):
    """returns new sp client plus the token for it"""
    if token is None:
        token = fetch_token(username)
        _LOGGER.info(f"{username}: NEW TOKEN FETCHED: {token}")

    if token in _SPOTI_CACHE:
        sp = _SPOTI_CACHE[token]
    else:
        sp_client = spotipy.Spotify(auth=token)
        sp = Spotter(username, sp_client)

    try:
        # check client stil good
        sp.client.current_user()
    except SpotifyException:
        if token in _SPOTI_CACHE:
            del _SPOTI_CACHE[token]
        _LOGGER.warning(f"{username}: TOKEN EXPIRED")
        # token may expire, ask for new
        token = fetch_token(username)
        _LOGGER.info(f"{username}: NEW TOKEN FETCHED: {token}")
        sp_client = spotipy.Spotify(auth=token)
        sp = Spotter(username, sp_client)
        _SPOTI_CACHE[token] = sp

    return sp, token
