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
@click.pass_context
def full_run(ctx):
    update_followed.invoke(ctx)
    generate_playlists.invoke(ctx)


@click.command()
def update_followed():
    click.echo("------------ RUN UPDATE USER ARTISTS")
    try:
        update_users_artists(CLIENT_ID, CLIENT_SECRET, CLIENT_URI)
    except Exception as exc:
        click.echo(f"failed with {exc}")
        _LOGGER.error(f"failed with {exc}")


@click.command()
def generate_playlists():
    click.echo("------------ RUN UPDATE USER PLAYLISTS")
    try:
        update_users_playlists(CLIENT_ID, CLIENT_SECRET, CLIENT_URI)
    except Exception as exc:
        click.echo(f"failed with {exc}")
        _LOGGER.error(f"failed with {exc}")


cli.add_command(update_followed)
cli.add_command(generate_playlists)
cli.add_command(full_run)

if __name__ == "__main__":
    cli()
