import os

import click
from dotenv import load_dotenv

from deneb.logger import get_logger
from deneb.main import update_users_follows

_LOGGER = get_logger(__name__)
load_dotenv()


CLIENT_ID = os.environ["SPOTIPY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SPOTIPY_CLIENT_SECRET"]
CLIENT_URI = os.environ["SPOTIPY_REDIRECT_URI"]


@click.group()
def cli():
    pass


@click.command()
def update_followed():
    _LOGGER.info("------------ RUN UPDATE ARTISTS ---------------")
    update_users_follows(CLIENT_ID, CLIENT_SECRET, CLIENT_URI)


@click.command()
def generate_playlists():
    print('humpte')


cli.add_command(update_followed)
cli.add_command(generate_playlists)

if __name__ == '__main__':
    cli()
