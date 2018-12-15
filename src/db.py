"""Database handling."""
import datetime
import json
import os
from typing import List, Tuple

from dotenv import load_dotenv
from peewee import (
    BooleanField, CharField, CompositeKey, DateField, DateTimeField,
    ForeignKeyField, ManyToManyField, Model, PostgresqlDatabase
)

from logger import get_logger

load_dotenv()

_DB = None
_LOGGER = get_logger(__name__)


def get_db() -> PostgresqlDatabase:
    global _DB
    if _DB is None:
        _DB = PostgresqlDatabase(
            os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            host=os.environ['DB_HOST'],
        )
    return _DB


def get_or_create_user(fb_id: str, username: str) -> Tuple['User', bool]:
    created = False
    try:
        user = User.get(User.fb_id == fb_id)
    except User.DoesNotExist:
        user = User.create(fb_id=fb_id, username=username)
        created = True
    except Exception as exc:
        _LOGGER.exception(f"user {fb_id} failed to create {exc}")
        raise

    return user, created


class Artist(Model):
    name = CharField()
    spotify_id = CharField(unique=True)
    timestamp = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = get_db()  # This model uses the "people.db" database.

    def __str__(self):
        return '{}'.format(self.name)

    def update_timestamp(self):
        self.timestamp = datetime.datetime.now()
        self.save()

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

    @classmethod
    def to_object(cls, artist):
        db_artist = None
        try:
            db_artist = cls.get(
                cls.spotify_id == artist['id'])
        except Exception:
            db_artist = cls(
                name=artist['name'], spotify_id=artist['id'])
            db_artist.save()
        return db_artist


class Market(Model):
    name = CharField()

    class Meta:
        database = get_db()

    def __repr__(self):
        return self.name

    @classmethod
    def to_obj(cls, market_name):
        market = None
        try:
            market = cls.get(cls.name == market_name)
        except Exception:
            market = cls.create(name=market_name)
            market.save()

        return market

    @classmethod
    def save_to_db(cls, market_name, no_db=False):
        if no_db:
            db_market = cls(name=market_name)
        else:
            db_market = cls.create(name=market_name)
        return db_market


class Album(Model):
    name = CharField()
    type = CharField()
    spotify_id = CharField()
    release = DateField(formats='%Y-%m-%d')
    timestamp = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = get_db()

    @property
    def uri(self):
        return f"spotify:{self.type}:{self.spotify_id}"

    def __str__(self):
        artists = [a.name for a in self.artists()]
        return '<{}> - {} ({})'.format(
            self.uri, ', '.join(artists), self.name, self.release)

    def update_timestamp(self):
        self.timestamp = datetime.datetime.now()
        self.save()

    def add_artist(self, artist):
        return AlbumArtist.create(album=self, artist=artist)

    def has_artist(self, artist):
        return (
            bool(
                len(
                    AlbumArtist
                    .select()
                    .where(
                        AlbumArtist.album == self,
                        AlbumArtist.artist_id == artist.id
                    )
                )
            )
        )

    def artists(self):
        return (
            Artist
            .select()
            .join(AlbumArtist, on=(AlbumArtist.artist_id == Artist.id))
            .where(AlbumArtist.album == self)
        )

    def add_market(self, market):
        return AvailableMarket.create(album=self, market=market)

    def remove_market(self, market):
        q = (AvailableMarket
             .delete()
             .where(
                 AvailableMarket.album == self,
                 AvailableMarket.market == market)
             )
        q.execute()

    def get_markets(self):
        return (
            Market
            .select()
            .join(
                AvailableMarket, on=(AvailableMarket.market_id == Market.id))
            .where(AvailableMarket.album == self)
        )

    @classmethod
    def save_to_db(
            cls, name, release_date, a_type,
            spotify_id, no_db=False
    ):
        if no_db:
            db_album = cls(
                name=name, release=release_date,
                type=a_type, spotify_id=spotify_id
            )
        else:
            db_album = cls.create(
                name=name, release=release_date,
                type=a_type, spotify_id=spotify_id
            )
        return db_album


class AlbumArtist(Model):
    album = ForeignKeyField(Album)
    artist = ForeignKeyField(Artist)

    class Meta:
        database = get_db()
        primary_key = CompositeKey('album', 'artist')


class AvailableMarket(Model):
    album = ForeignKeyField(Album)
    market = ForeignKeyField(Market)

    class Meta:
        database = get_db()
        primary_key = CompositeKey('album', 'market')

    def __repr__(self):
        return '{} [{}]'.format(self.album.name, self.market.name)


class User(Model):
    username = CharField()
    fb_id = CharField()
    market = ForeignKeyField(Market, null=True)
    initialized = BooleanField(default=False)
    following = ManyToManyField(Artist, backref="followers")
    spotify_token = CharField(max_length=1000)
    state_id = CharField()

    def __str__(self) -> str:
        return f"<user:{self.fb_id}:{self.username}>"

    def following_ids(self: 'User') -> List[Artist]:
        return self.following.select(Artist.id)

    def get_seen_albums(self):
        return (
            Album
            .select()
            .join(
                SeenAlbum,
                on=(SeenAlbum.album_id == Album.id))
            .where(SeenAlbum.user == self)
        )

    def released_from_weekday(self, date):
        return (
            Album
            .select()
            .join(
                AvailableMarket, on=(AvailableMarket.album_id == Album.id)
            )
            .join(
                AlbumArtist, on=(AlbumArtist.album_id == Album.id)
            )
            .where(
                AvailableMarket.market == self.market,
                AlbumArtist.artist_id << self.following_ids(),
                (Album.release.year == date.year) &
                (Album.release.month == date.month) &
                (Album.release.day >= date.day)
            )
            .distinct()
        )

    def sync_data(self, sp):
        self.market = Market.to_obj(sp.userdata['country'])
        self.username = sp.userdata['id']
        self.spotify_token = json.dumps(
            sp.client.client_credentials_manager.token_info)
        self.initialized = True
        self.save()

    def new_albums(self, date=None, seen=False):
        return (
            Album
            .select()
            .join(
                AlbumArtist, on=(AlbumArtist.album_id == Album.id)
            )
            .where()
        )

    def get_all_albums(self):
        return (
            Album
            .select(Album.id)
            .join(
                AlbumArtist, on=(AlbumArtist.album_id == Album.id)
            )
            .where(
                AlbumArtist.artist_id << self.following_ids()
            )
        )

    def add_seen_album(self, album):
        SeenAlbum.create(user=self, album=album)

    def add_follows(self, artists):
        for artist in artists:
            self.following.add(artist)

    def remove_follows(self, artists):
        for artist in artists:
            self.following.remove(artist)

    class Meta:
        database = get_db()


ArtistFollowers = User.following.get_through_model()


class SeenAlbum(Model):
    album = ForeignKeyField(Album)
    user = ForeignKeyField(User)

    class Meta:
        database = get_db()


Artist.create_table(fail_silently=True)
Market.create_table(fail_silently=True)
User.create_table(fail_silently=True)
Album.create_table(fail_silently=True)
AvailableMarket.create_table(fail_silently=True)
SeenAlbum.create_table(fail_silently=True)
ArtistFollowers.create_table(fail_silently=True)
AlbumArtist.create_table(fail_silently=True)
