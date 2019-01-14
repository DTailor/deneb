"""Database handling."""

import asyncio
import datetime
import os

from gino import Gino
from dotenv import load_dotenv

from logger import get_logger

load_dotenv()

_DB = Gino()
_LOGGER = get_logger(__name__)
_OBJECTS = None


class Album(_DB.Model):  # type: ignore
    __tablename__ = "album"

    id = _DB.Column(_DB.Integer, primary_key=True)
    name = _DB.Column(_DB.String())
    type = _DB.Column(_DB.String())
    spotify_id = _DB.Column(_DB.String())
    release = _DB.Column(_DB.Date)
    timestamp = _DB.Column(_DB.DateTime, default=datetime.datetime.now)

    @property
    def uri(self):
        return f"spotify:{self.type}:{self.spotify_id}"

    def __str__(self):
        # artists = ", ".join([a.name for a in self.artists()])
        # return f"<{self.uri}> - {artists} ({self.name} [{self.release}])"
        return f"<{self.uri}> - ({self.name} [{self.release}])"

    def __repr__(self):
        return self.__str__()


class Artist(_DB.Model):  # type: ignore
    __tablename__ = "artist"

    id = _DB.Column(_DB.Integer, primary_key=True)
    name = _DB.Column(_DB.String())
    spotify_id = _DB.Column(_DB.String())  # somehow unique
    timestamp = _DB.Column(_DB.DateTime, default=datetime.datetime.now)

    def __init__(self, **kw):
        super().__init__(**kw)
        self._followers = set()

    @property
    def followers(self):
        return self._followers

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return self.__str__()


class UserXArtist(_DB.Model):  # type: ignore
    __tablename__ = "user_artist_through"

    user_id = _DB.Column(_DB.Integer, _DB.ForeignKey("user.id"))
    artist_id = _DB.Column(_DB.Integer, _DB.ForeignKey("artist.id"))


class User(_DB.Model):  # type: ignore
    __tablename__ = "user"

    id = _DB.Column(_DB.Integer, primary_key=True)
    username = _DB.Column(_DB.String())
    fb_id = _DB.Column(_DB.String())
    display_name = _DB.Column(_DB.String(), default="")
    # market = ForeignKeyField(Market, null=True)
    # following = ManyToManyField(Artist, backref="followers")
    spotify_token = _DB.Column(_DB.String())
    state_id = _DB.Column(_DB.String())

    def __init__(self, **kw):
        super().__init__(**kw)
        self._following = set()

    @property
    def following(self):
        return self._following

    @following.setter  # type: ignore
    def add_follow(self, artist):
        self._following.add(artist)
        artist._followers.add(self)

    def __str__(self) -> str:
        base = f"spotify:user:{self.username}>"
        if self.display_name:
            base = f"<{self.display_name}:{base}"
        else:
            base = f"<{base}"
        return base

    def __repr__(self) -> str:
        return self.__str__()

    async def get_followed_artists(self):
        # query = User.outerjoin(UserXArtist).outerjoin(Artist).select()
        # parents = await query.gino.load(
        #     Parent.distinct(Parent.id).load(add_child=Child.distinct(Child.id))
        # ).all()
        pass

    @staticmethod
    async def get_by_username(username):
        query, loader = USER_WITH_FOLLOWS
        return await query.where(User.username == username).gino.load(loader).first()

    async def released_from_weekday(self, date):
        albums = await Album.select(Album).where(Album.release >= date).gino.all()
        following_artists = await self.get_followed_artists()

        # return (
        #     Album.select()
        #     .join(AvailableMarket, on=(AvailableMarket.album_id == Album.id))
        #     .join(AlbumArtist, on=(AlbumArtist.album_id == Album.id))
        #     .where(
        #         AvailableMarket.market == self.market,
        #         AlbumArtist.artist_id << self.following_ids(),
        #         Album.release >= date,
        #     )
        #     .distinct()
        # )

# some loaders (query, loade)
# query.gino.load(loader).all()
USER_WITH_FOLLOWS = (
    User.outerjoin(UserXArtist).outerjoin(Artist).select(),
    User.distinct(User.id).load(add_follow=Artist.distinct(Artist.id)),
)

async def config_db():
    global _DB
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]
    host = os.environ["DB_HOST"]
    name = os.environ["DB_NAME"]
    await _DB.set_bind(f"postgresql+asyncpg://{user}:{password}@{host}:5432/{name}")
    await _DB.gino.create_all()

    # query = User.outerjoin(UserXArtist).outerjoin(Artist).select()
    # await query.gino.load(
    #     User.distinct(User.id).load(add_follow=Artist.distinct(Artist.id))
    # ).all()


asyncio.get_event_loop().run_until_complete(config_db())
