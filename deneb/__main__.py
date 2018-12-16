import os

import click
from dotenv import load_dotenv

from deneb.logger import get_logger
from deneb.spotify.users import update_users_artists
from deneb.spotify.weekly_releases import update_users_playlists

load_dotenv()

_LOGGER = get_logger(__name__)


CLIENT_ID = os.environ["SPOTIPY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SPOTIPY_CLIENT_SECRET"]
CLIENT_URI = os.environ["SPOTIPY_REDIRECT_URI"]


@click.group()
def cli():
    pass


@click.command()
def update_followed():
    _LOGGER.debug("------------ RUN UPDATE USER ARTISTS")
    try:
        update_users_artists(CLIENT_ID, CLIENT_SECRET, CLIENT_URI)
    except Exception as exc:
        print(f"failed with {exc}")
        _LOGGER.error(f"failed with {exc}")


@click.command()
def generate_playlists():
    _LOGGER.info("------------ RUN UPDATE USER PLAYLISTS")
    try:
        update_users_playlists(CLIENT_ID, CLIENT_SECRET, CLIENT_URI)
    except Exception as exc:
        print(f"failed with {exc}")
        _LOGGER.error(f"failed with {exc}")


cli.add_command(update_followed)
cli.add_command(generate_playlists)

if __name__ == '__main__':
    cli()
