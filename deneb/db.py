"""Database handling."""

import datetime
import json
import os

from dotenv import load_dotenv
from tortoise import Tortoise, fields
from tortoise.models import Model

from deneb.logger import get_logger

load_dotenv()

_LOGGER = get_logger(__name__)


async def init_db() -> None:
    host = os.environ["DB_HOST"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]
    name = os.environ["DB_NAME"]
    dsn = f"postgres://{user}:{password}@{host}:5432/{name}"

    await Tortoise.init(
        db_url=dsn,
        modules={"models": ["deneb.db"]},
    )


async def close_db() -> None:
    await Tortoise.close_connections()


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
    timestamp = fields.DatetimeField(default=datetime.datetime.now)
    artists = fields.ManyToManyField(
        "models.Artist", through="album_artist_through", related_name="albums"
    )
    markets = fields.ManyToManyField("models.Market", through="album_market_through")

    @property
    def uri(self):
        return f"spotify:{self.type}:{self.spotify_id}"

    def __str__(self):
        return f"<{self.uri}> - ({self.name} [{self.release}])"

    def __repr__(self):
        return self.__str__()

    async def update_timestamp(self):
        await Album.filter(id=self.id).update(timestamp=datetime.datetime.now())


class Artist(Model):  # type: ignore
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    spotify_id = fields.CharField(max_length=255)
    timestamp = fields.DatetimeField(default=datetime.datetime.now)

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

    async def update_timestamp(self):
        await Artist.filter(id=self.id).update(timestamp=datetime.datetime.now())


class User(Model):  # type: ignore
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=255)
    fb_id = fields.CharField(max_length=255)
    display_name = fields.CharField(max_length=255, default="")
    market = fields.ForeignKeyField("models.Market", null=True)
    artists = fields.ManyToManyField("models.Artist", through="user_artist_through")
    spotify_token = fields.CharField(max_length=255)
    state_id = fields.CharField(max_length=255)

    def __str__(self) -> str:
        base = f"spotify:user:{self.username}>"
        if self.display_name:
            base = f"<{self.display_name}:{base}"
        else:
            base = f"<{base}"
        return base

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
        return await Album.filter(
            release__gte=date, artists__id__in=followed_ids, markets__id=self.market_id
        )
