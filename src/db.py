"""Database handling."""
import datetime
import os

from peewee import (
    BooleanField, CharField, CompositeKey, DateField, DateTimeField,
    ForeignKeyField, ManyToManyField, Model, PostgresqlDatabase
)

from logger import get_logger

assert os.environ['DB_NAME']
assert os.environ['DB_USER']
assert os.environ['DB_PASSWORD']

_DB = None
_LOGGER = get_logger(__name__)

def get_db():
    global _DB
    if _DB is None:
        _DB = PostgresqlDatabase(os.environ['DB_NAME'], user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'])
    return _DB


def get_or_create_user(fb_id):
    created = False
    try:
        user = User.get(User.fb_id == fb_id)
    except User.DoesNotExist:
        _LOGGER.info(f"new user created in db: {user}")
        user = User.create(fb_id=fb_id)
        created = True
    return user, created


class Artist(Model):
    name = CharField()
    spotify_id = CharField(unique=True)
    timestamp = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = get_db()  # This model uses the "people.db" database.

    def __str__(self):
        return '{}'.format(self.name)

    def can_upate(self, hours_delta=4):
        """check if artist can be updated

        returns True if last update time is bigger
        the the hours_delta, else False
        """
        if not self.timestamp:
            return True
        delta = datetime.datetime.now() - self.timestamp
        if delta.total_seconds() / 3600 < hours_delta:
            return True
        return False

    @classmethod
    def to_object(cls, artist):
        db_artist = None
        try:
            db_artist = cls.get(cls.spotify_id == artist['id'])
        except:
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
        except:
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

    def __str__(self):
        artists = [a.name for a in self.artists()]
        album_type = 'track' if self.type == 'track' else 'album'
        return '<spotify:{}:{}> {} - {} ({})'.format(
            album_type, self.spotify_id, ', '.join(artists), self.name, self.release)

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
    def save_to_db(                                         # pylint: disable=C0111
            cls, name, release_date, a_type,
            spotify_id, no_db=False
        ):                                                  # pylint: disable=R0913
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
    fb_id = CharField()
    market = ForeignKeyField(Market, null=True)
    initialised = BooleanField(default=False)
    following = ManyToManyField(Artist)

    def __str__(self):
        return f"<user:{self.fb_id}:{self.market.name}>"

    def get_seen_albums(self):
        return (
            Album
            .select()
            .join(
                SeenAlbum,
                on=(SeenAlbum.album_id == Album.id))
            .where(SeenAlbum.user == self)
        )

    def on_date_release(self, date):
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
                AvailableMarket.market_id == self.market_id,
                AlbumArtist.artist << self.following,
                (Album.release.year == date.year) &
                (Album.release.month == date.month) &
                (Album.release.day == date.day)
            )
            .distinct()
        )

    def update_market(self, user_data):
        self.market = Market.to_obj(user_data['country'])
        self.save()

    def new_albums(self, date=None, seen=False):
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
                AvailableMarket.market_id == self.market_id,
                AlbumArtist.artist << self.following,
                ~(AlbumArtist.album << self.get_seen_albums()),
                # (Album.release.year == today.year) &
                # (Album.release.month == today.month) &
                # (Album.release.day == today.day)
            )
            .distinct()
        )

    def get_all_albums(self):
        return (
            Album
            .select()
            .join(
                AlbumArtist, on=(AlbumArtist.album_id == Album.id)
            )
            .where(
                AlbumArtist.artist << self.following
            )
            .distinct()
        )

    def get_all_albums_market(self):
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
                AvailableMarket.market_id == self.market_id,
                AlbumArtist.artist << self.following
            )
            .distinct()
        )

    def add_seen_album(self, album):
        SeenAlbum.create(user=self, album=album)


    def add_follows(self, artists):
        for artist in artists:
            self.following.add(artist)

    def remove_follows(self, artists):
        for artist in artists:
            self.following.remove(artists)


    class Meta:
        database = get_db()

    def __repr__(self):
        return '<{}; following: {} artists>'.format(self.fb_id, len(self.following))


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
