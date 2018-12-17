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


@click.option('--force', is_flag=True)
@click.option('--user')
@click.command()
@click.pass_context
def full_run(ctx, user, force):
    update_followed.invoke(ctx)
    ctx.params = {
        'user': user,
    }
    update_playlists.invoke(ctx)


@click.option('--force', is_flag=True)
@click.option('--user')
@click.command()
def update_followed(user, force):
    click.echo("------------ RUN UPDATE USER ARTISTS")
    try:
        update_users_artists(CLIENT_ID, CLIENT_SECRET, CLIENT_URI, user, force)
    except Exception:
        _LOGGER.exception(f"uhhh ohhhhhhhhhhhhh task failed")


@click.option('--user')
@click.command()
def update_playlists(user):
    click.echo("------------ RUN UPDATE USER PLAYLISTS")
    try:
        update_users_playlists(CLIENT_ID, CLIENT_SECRET, CLIENT_URI, user)
    except Exception:
        _LOGGER.exception(f"uhhh ohhhhhhhhhhhhh task failed")


cli.add_command(update_followed)
cli.add_command(update_playlists)
cli.add_command(full_run)

if __name__ == "__main__":
    cli()
