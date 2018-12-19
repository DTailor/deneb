import os

import click
from dotenv import load_dotenv

from deneb.logger import get_logger
from deneb.spotify.users import update_users_artists
from deneb.spotify.weekly_releases import update_users_playlists
from deneb.structs import SpotifyKeys, Chatboi

load_dotenv()

_LOGGER = get_logger(__name__)


SPOTIFY_KEYS = SpotifyKeys(
    os.environ["SPOTIPY_CLIENT_ID"],
    os.environ["SPOTIPY_CLIENT_SECRET"],
    os.environ["SPOTIPY_REDIRECT_URI"],
)

CHATBOI = Chatboi(
    os.environ["CHAPTAIN_KEY"],
    os.environ["CHAPTAIN_URL"],
    False,
)


@click.group()
def cli():
    pass


@click.option("--force", is_flag=True)
@click.option("--notify", is_flag=True)
@click.option("--user")
@click.command()
@click.pass_context
def full_run(ctx, user, force, notify):
    orig_params = ctx.params.copy()

    ctx.params = {
        "user": orig_params["user"],
        "force": orig_params.get("force", False),
    }
    update_followed.invoke(ctx)

    ctx.params = {
        "user": orig_params["user"],
        "notify": orig_params.get("notify", False)
    }
    update_playlists.invoke(ctx)


@click.option("--force", is_flag=True)
@click.option("--user")
@click.command()
def update_followed(user, force):
    click.echo("------------ RUN UPDATE USER ARTISTS")
    try:
        update_users_artists(SPOTIFY_KEYS, user, force)
    except Exception:
        _LOGGER.exception(f"uhhh ohhhhhhhhhhhhh task failed")


@click.option("--notify", is_flag=True)
@click.option("--user")
@click.command()
def update_playlists(user, notify):
    click.echo("------------ RUN UPDATE USER PLAYLISTS")
    CHATBOI.notify = notify
    try:
        update_users_playlists(SPOTIFY_KEYS, CHATBOI, user)
    except Exception:
        _LOGGER.exception(f"uhhh ohhhhhhhhhhhhh task failed")


cli.add_command(update_followed)
cli.add_command(update_playlists)
cli.add_command(full_run)

if __name__ == "__main__":
    cli()
