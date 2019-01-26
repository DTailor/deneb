"""Database handling."""

import asyncio
import datetime
from tortoise.models import Model
import json
import os
from tortoise import Tortoise
from tortoise import fields

from dotenv import load_dotenv

from deneb.logger import get_logger

load_dotenv()

_LOGGER = get_logger(__name__)


async def init_db() -> None:

    host = os.environ["DB_HOST"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]
    name = os.environ["DB_NAME"]
    await Tortoise.init(
        db_url=f"postgres://{user}:{password}@{host}:5432/{name}",
        modules={"models": ["deneb.db_async"]},
    )


async def close_db() -> None:
    await Tortoise.close_connections()


class Album(Model):  # type: ignore
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    type = fields.CharField(max_length=255)
    spotify_id = fields.CharField(max_length=255)
    release = fields.DateField()
    timestamp = fields.DatetimeField(default=datetime.datetime.now)

    @property
    def uri(self):
        return f"spotify:{self.type}:{self.spotify_id}"

    def __str__(self):
        # artists = ", ".join([a.name for a in self.artists()])
        # return f"<{self.uri}> - {artists} ({self.name} [{self.release}])"
        return f"< {self.uri} - {self.name} >"

    def __repr__(self):
        return self.__str__()


class Artist(Model):  # type: ignore
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    spotify_id = fields.CharField(max_length=255)
    timestamp = fields.DatetimeField(default=datetime.datetime.now)

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return self.__str__()


# class UserXArtist(Model):  # type: ignore
#     __tablename__ = "user_artist_through"

#     user_id = _DB.Column(_DB.Integer, _DB.ForeignKey("user.id"))
#     artist_id = _DB.Column(_DB.Integer, _DB.ForeignKey("artist.id"))


class User(Model):  # type: ignore
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=255)
    fb_id = fields.CharField(max_length=255)
    display_name = fields.CharField(max_length=255, default="")
    # market = ForeignKeyField(Market, null=True)
    # following = ManyToManyField(Artist, backref="followers")
    spotify_token = fields.CharField(max_length=255)
    state_id = fields.CharField(max_length=255)

#     @property
#     def following(self):
#         return self._following

#     @following.setter  # type: ignore
#     def add_follow(self, artist):
#         self._following.add(artist)
#         artist._followers.add(self)

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
            raise ValueError(f"""
            no refresh token present.
            CRED_MAN: {sp.client.client_credentials_manager}
            TOK_INF: {sp.client.client_credentials_manager.token_info}
            IN_DB: {self.spotify_token}
            """)
        # self.market = Market.to_obj(sp.userdata["country"])
        await User.filter(id=self.id).update(
            username=sp.userdata["id"],
            display_name=sp.userdata["display_name"],
            spotify_token=json.dumps(sp.client.client_credentials_manager.token_info),
        )

#     async def get_followed_artists(self):
#         # query = User.outerjoin(UserXArtist).outerjoin(Artist).select()
#         # parents = await query.gino.load(
#         #     Parent.distinct(Parent.id).load(add_child=Child.distinct(Child.id))
#         # ).all()
#         pass

#     @staticmethod
#     async def get_by_username(username):
#         query, loader = USER_WITH_FOLLOWS
#         return await query.where(User.username == username).gino.load(loader).first()

#     async def released_from_weekday(self, date):
#         albums = await Album.select(Album).where(Album.release >= date).gino.all()
#         following_artists = await self.get_followed_artists()

#         # return (
#         #     Album.select()
#         #     .join(AvailableMarket, on=(AvailableMarket.album_id == Album.id))
#         #     .join(AlbumArtist, on=(AlbumArtist.album_id == Album.id))
#         #     .where(
#         #         AvailableMarket.market == self.market,
#         #         AlbumArtist.artist_id << self.following_ids(),
#         #         Album.release >= date,
#         #     )
#         #     .distinct()
#         # )

# # some loaders (query, loade)
# # query.gino.load(loader).all()
# USER_WITH_FOLLOWS = (
#     User.outerjoin(UserXArtist).outerjoin(Artist).select(),
#     User.distinct(User.id).load(add_follow=Artist.distinct(Artist.id)),
# )

# async def config_db():
#     global _DB
#     user = os.environ["DB_USER"]
#     password = os.environ["DB_PASSWORD"]
#     host = os.environ["DB_HOST"]
#     name = os.environ["DB_NAME"]
#     await _DB.set_bind(f"postgresql+asyncpg://{user}:{password}@{host}:5432/{name}")
#     await _DB.gino.create_all()

#     # query = User.outerjoin(UserXArtist).outerjoin(Artist).select()
#     # await query.gino.load(
#     #     User.distinct(User.id).load(add_follow=Artist.distinct(Artist.id))
#     # ).all()


# asyncio.get_event_loop().run_until_complete(config_db())
