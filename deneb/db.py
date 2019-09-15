"""Database handling."""

import datetime
import json
import os
from typing import Tuple

from tortoise import exceptions, fields
from tortoise.models import Model

from deneb.logger import get_logger
from deneb.tools import generate_release_date
from deneb.tortoise_pool import PoolTortoise

_LOGGER = get_logger(__name__)


async def init_db() -> None:
    host = os.environ["DB_HOST"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]
    name = os.environ["DB_NAME"]
    dsn = f"postgres://{user}:{password}@{host}:5432/{name}"

    await PoolTortoise.init(db_url=dsn, modules={"models": ["deneb.db"]})


async def close_db() -> None:
    await PoolTortoise.close_connections()


class Market(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)

    def __repr__(self):
        return self.name


class Album(Model):  # type: ignore
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    type = fields.CharField(max_length=255)
    spotify_id = fields.CharField(max_length=255)
    release = fields.DateField()
    created_at = fields.DatetimeField(auto_now_add=True)
    artists = fields.ManyToManyField(
        "models.Artist", through="artist_albums", related_name="albums"
    )
    markets = fields.ManyToManyField("models.Market", through="album_markets")

    @property
    def uri(self):
        return f"spotify:{self.type}:{self.spotify_id}"

    def __str__(self):
        return f"<{self.uri}> - ({self.name} [{self.release}])"

    def __repr__(self):
        return self.__str__()

    @classmethod
    async def get_or_create(
        cls, album: dict, retry: bool = True
    ) -> Tuple["Album", bool]:
        created = False

        try:
            db_album = await Album.get(spotify_id=album["id"])
        except exceptions.DoesNotExist:
            release_date = generate_release_date(
                album["release_date"], album["release_date_precision"]
            )
            try:
                db_album = await Album.create(
                    name=album["name"],
                    release=release_date,
                    type=album["type"],
                    spotify_id=album["id"],
                )
                created = True
            except exceptions.IntegrityError:
                if retry:
                    # this is a race condition experienced when multiple
                    # users are updating their artist list and
                    # user A failed to fetch the album, and while
                    # trying to create it, another user B goes past the same
                    # flow so that user A fails to create the album as it is
                    # already in there
                    return await cls.get_or_create(album, retry=False)
                raise

        return db_album, created


class Artist(Model):  # type: ignore
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    spotify_id = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now_add=True)
    synced_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return self.__str__()

    def can_update(self, hours_delta=4):
        """check if artist can be updated

        returns True if last update time is bigger
        the the hours_delta, else False
        """
        if not self.timestamp:
            return True
        delta = datetime.datetime.now() - self.timestamp
        if delta.total_seconds() / 3600 > hours_delta:
            return True
        return False

    async def update_synced_at(self):
        self.synced_at = datetime.datetime.now()
        await self.save()


class User(Model):  # type: ignore
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=255)
    fb_id = fields.CharField(max_length=255)
    display_name = fields.CharField(max_length=255, default="")
    market = fields.ForeignKeyField("models.Market", null=True)
    artists = fields.ManyToManyField("models.Artist", through="user_followed_artists")
    spotify_token = fields.CharField(max_length=255, null=True)

    def __str__(self) -> str:
        return f"<spotify:user:{self.username}>"

    def __repr__(self) -> str:
        return self.__str__()

    async def async_data(self, sp):
        if "refresh_token" not in sp.client.client_credentials_manager.token_info:
            raise ValueError(
                f"""
            no refresh token present.
            CRED_MAN: {sp.client.client_credentials_manager}
            TOK_INF: {sp.client.client_credentials_manager.token_info}
            IN_DB: {self.spotify_token}
            """
            )
        market, _ = await Market.get_or_create(name=sp.userdata["country"])
        await User.filter(id=self.id).update(
            username=sp.userdata["id"],
            display_name=sp.userdata["display_name"],
            spotify_token=json.dumps(sp.client.client_credentials_manager.token_info),
            market_id=market.id,
        )

    async def released_from_weekday(self, date):
        followed_ids = await self.artists.filter().values_list("id")
        followed_ids = [a[0] for a in followed_ids]
        if not followed_ids:
            _LOGGER.info(f"user {self} has no followers")
            return []
        return await Album.filter(release__gte=date, artists__id__in=followed_ids)
