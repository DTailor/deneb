from tortoise import fields
from tortoise.models import Model


class Market(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)

    def __repr__(self):
        return self.name
