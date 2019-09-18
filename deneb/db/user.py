import json

from tortoise import fields
from tortoise.models import Model

from deneb.logger import get_logger

_LOGGER = get_logger(__name__)


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
