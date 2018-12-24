import os

import click
from dotenv import load_dotenv

from deneb.logger import get_logger
from deneb.spotify.users import update_users_artists
from deneb.spotify.weekly_releases import update_users_playlists
from deneb.structs import SpotifyKeys, FBAltert

load_dotenv()

_LOGGER = get_logger(__name__)


SPOTIFY_KEYS = SpotifyKeys(
    os.environ["SPOTIPY_CLIENT_ID"],
    os.environ["SPOTIPY_CLIENT_SECRET"],
    os.environ["SPOTIPY_REDIRECT_URI"],
)


def get_fb_alert(notify: bool) -> FBAltert:
    return FBAltert(
        os.environ["FB_API_KEY"],
        os.environ["FB_API_URL"],
        notify,
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
    fb_alert = get_fb_alert(notify)
    try:
        update_users_playlists(SPOTIFY_KEYS, fb_alert, user)
    except Exception:
        _LOGGER.exception(f"uhhh ohhhhhhhhhhhhh task failed")


cli.add_command(update_followed)
cli.add_command(update_playlists)
cli.add_command(full_run)

if __name__ == "__main__":
    cli()
