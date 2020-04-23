import datetime

from tortoise import fields
from tortoise.models import Model


class Artist(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    spotify_id = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now_add=True)
    synced_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'deneb"."artist'

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return self.__str__()

    def can_update(self, hours_delta=4):
        """check if artist can be updated

        returns True if last update time is bigger
        the the hours_delta, else False
        """
        if not self.synced_at:
            return True
        delta = datetime.datetime.now() - self.synced_at
        if delta.total_seconds() / 3600 > hours_delta:
            return True
        return False

    async def update_synced_at(self):
        self.synced_at = datetime.datetime.now()
        await self.save()
