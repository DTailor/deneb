from typing import Tuple

from tortoise import exceptions, fields
from tortoise.models import Model

from deneb.tools import generate_release_date


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
