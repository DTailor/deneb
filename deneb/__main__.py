import asyncio
import os

import click
import uvloop
from dotenv import load_dotenv

load_dotenv()  # noqa

from deneb.db import close_db, init_db
from deneb.logger import get_logger
from deneb.spotify.users_following import sync_users_artists
from deneb.spotify.weekly_releases import update_users_playlists
from deneb.spotify.yearly_liked import update_users_playlists_liked_by_year
from deneb.structs import FBAlert, SpotifyKeys

uvloop.install()

_LOGGER = get_logger(__name__)


SPOTIFY_KEYS = SpotifyKeys(
    os.environ["SPOTIPY_CLIENT_ID"],
    os.environ["SPOTIPY_CLIENT_SECRET"],
    os.environ["SPOTIPY_REDIRECT_URI"],
)


def runner(func, args):
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(init_db())
        loop.run_until_complete(func(*args))
    except Exception:
        _LOGGER.exception(f"task {func} interrupted; args: {args[1:]};")
    finally:
        loop.run_until_complete(close_db())
        loop.close()


def get_fb_alert(notify: bool) -> FBAlert:
    return FBAlert(os.environ["FB_API_KEY"], os.environ["FB_API_URL"], notify)


@click.group()
def cli():
    pass


@click.command()
@click.option("--user")
@click.option("--force", is_flag=True)
@click.option("--notify", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--all-markets", is_flag=True)
@click.option("--year")
@click.pass_context
def full_run(ctx, user, force, notify, dry_run, all_markets, year):
    orig_params = ctx.params.copy()

    ctx.params = {
        "user": orig_params["user"],
        "force": orig_params.get("force", False),
        "dry_run": orig_params.get("dry_run", False),
        "all_markets": orig_params.get("all_markets", False),
    }
    update_followed.invoke(ctx)

    ctx.params = {
        "user": orig_params["user"],
        "notify": orig_params.get("notify", False),
        "dry_run": orig_params.get("dry_run", False),
        "all_markets": orig_params.get("all_markets", False),
    }
    update_playlists.invoke(ctx)

    ctx.params = {
        "user": orig_params["user"],
        "year": orig_params.get("year", None),
        "notify": orig_params.get("notify", False),
        "dry_run": orig_params.get("dry_run", False),
    }
    update_playlists_yearly_liked.invoke(ctx)


@click.command()
@click.option("--user")
@click.option("--force", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--all-markets", is_flag=True)
def update_followed(user, force, dry_run, all_markets):
    _LOGGER.info("running: update user followed artists and artist albums")
    runner(sync_users_artists, (SPOTIFY_KEYS, user, force, dry_run, all_markets))


@click.command()
@click.option("--user")
@click.option("--notify", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--all-markets", is_flag=True)
def update_playlists(user, notify, dry_run, all_markets):
    _LOGGER.info("running: update users spotify weekly playlists")
    fb_alert = get_fb_alert(notify)
    runner(update_users_playlists, (SPOTIFY_KEYS, fb_alert, user, dry_run, all_markets))


@click.command()
@click.option("--user")
@click.option("--year")
@click.option("--notify", is_flag=True)
@click.option("--dry-run", is_flag=True)
def update_playlists_yearly_liked(user, year, notify, dry_run):
    _LOGGER.info("running: update users spotify liked by year playlist")
    fb_alert = get_fb_alert(notify)
    runner(
        update_users_playlists_liked_by_year,
        (SPOTIFY_KEYS, fb_alert, user, year, dry_run),
    )


cli.add_command(update_playlists_yearly_liked)
cli.add_command(update_followed)
cli.add_command(update_playlists)
cli.add_command(full_run)

if __name__ == "__main__":
    cli()
