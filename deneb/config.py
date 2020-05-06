"""Module to store app config"""
import os

VERSION = "v2.2.1"


class Config:
    USERS_TASKS_AMOUNT = 5
    ALBUMS_TASKS_AMOUNT = 20
    ARTISTS_TASKS_AMOUNT = 20
    PLAYLIST_NAME_PREFIX = os.environ["DENEB_PLAYLIST_NAME_PREFIX"]
