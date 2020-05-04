import asyncio
import os

import uvloop
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init, worker_process_shutdown

from deneb.config import VERSION
from deneb.db import close_db, init_db
from deneb.logger import get_logger
from deneb.structs import FBAlert, SpotifyKeys
from deneb.spotify.yearly_liked import update_users_playlists_liked_by_year

_LOGGER = get_logger(__name__)

SPOTIFY_KEYS = SpotifyKeys(
    os.environ["SPOTIPY_CLIENT_ID"],
    os.environ["SPOTIPY_CLIENT_SECRET"],
    os.environ["SPOTIPY_REDIRECT_URI"],
)

uvloop.install()


@worker_process_init.connect
def init_worker(*args, **kwargs):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(close_db())


app = Celery(f"deneb-{VERSION}")


@app.task()
def liked_task():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        update_users_playlists_liked_by_year(
            SPOTIFY_KEYS,
            FBAlert(os.environ["FB_API_KEY"], os.environ["FB_API_URL"], True),
            None,
            None,
            dry_run=False,
        )
    )


config = {
    "beat_schedule": {
        "liked-sorted-yearly": {
            "task": "celery_ship.liked_task",
            "schedule": crontab(hour="*"),
        },
    },
    "timezone": "Europe/Bucharest",
}

app.conf.update(config)
