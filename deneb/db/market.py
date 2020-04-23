from tortoise import fields
from tortoise.models import Model


class Market(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)

    class Meta:
        table = 'deneb"."market'

    def __repr__(self):
        return self.name
