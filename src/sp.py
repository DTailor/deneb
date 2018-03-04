"""Spotify connection handling"""

import os

import spotipy
from spotipy import util
from spotipy.client import SpotifyException

# check spotify environ keys are set
assert os.environ['SPOTIPY_CLIENT_ID']
assert os.environ['SPOTIPY_CLIENT_SECRET']
assert os.environ['SPOTIPY_REDIRECT_URI']


def fetch_token(username):
    """gen an access token"""
    token = util.prompt_for_user_token(
        username=username,
        scope='user-follow-read user-read-private',
        client_id=os.environ['SPOTIPY_CLIENT_ID'],
        client_secret=os.environ['SPOTIPY_CLIENT_SECRET'],
        redirect_uri=os.environ['SPOTIPY_REDIRECT_URI']
    )
    return token


def get_sp_client(username, token=None):
    """returns new sp client plus the token for it"""
    if token is None:
        token = fetch_token(username)
    sp_client = spotipy.Spotify(auth=token)
    try:
        sp_client.current_user()
    except SpotifyException:
        # token may expire, ask for new
        token = fetch_token(username)
        sp_client = spotipy.Spotify(auth=token)
    return sp_client, token
