"""Database handling."""

import os

from deneb.db.album import Album
from deneb.db.artist import Artist
from deneb.db.market import Market
from deneb.db.user import User
from deneb.tortoise_pool import PoolTortoise


async def init_db() -> None:
    host = os.environ["DB_HOST"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]
    name = os.environ["DB_NAME"]
    dsn = f"postgres://{user}:{password}@{host}:5432/{name}"

    await PoolTortoise.init(db_url=dsn, modules={"models": ["deneb.db"]})


async def close_db() -> None:
    await PoolTortoise.close_connections()

__all__ = ["Album", "Artist", "Market", "User", "PoolTortoise", "init_db", "close_db"]
