"""Database handling."""
import datetime
import os

from peewee import (
    BooleanField, CharField, CompositeKey, DateField, DateTimeField,
    ForeignKeyField, ManyToManyField, Model, PostgresqlDatabase
)


assert os.environ['DB_NAME']
assert os.environ['DB_USER']
assert os.environ['DB_PASSWORD']

_DB = None


def get_db():
    global _DB
    if _DB is None:
        _DB = PostgresqlDatabase(os.environ['DB_NAME'], user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'])
    return _DB


def get_or_create_user(fb_id):
    try:
        user = User.get(User.fb_id == fb_id)
    except User.DoesNotExist:
        user = User.create(fb_id=fb_id)
    return user


class Artist(Model):
    name = CharField()
    spotify_id = CharField(unique=True)
    timestamp = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = get_db()  # This model uses the "people.db" database.

    def __repr__(self):
        return '{}'.format(self.name)


class Market(Model):
    name = CharField()

    class Meta:
        database = get_db()

    def __repr__(self):
        return self.name


class Album(Model):
    name = CharField()
    type = CharField()
    spotify_id = CharField()
    release = DateField(formats='%Y-%m-%d')
    timestamp = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = get_db()

    def __repr__(self):
        artists = [a.name for a in self.artists()]
        album_type = 'track' if self.type == 'track' else 'album'
        return '<spotify:{}:{}> {} - {} ({})'.format(
            album_type, self.spotify_id, ', '.join(artists), self.name, self.release)

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
        date = datetime.datetime.strptime(date, '%Y-%m-%d')
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

    class Meta:
        database = get_db()

    def __repr__(self):
        return self.fb_id


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

