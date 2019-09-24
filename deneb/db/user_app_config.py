from tortoise import fields
from tortoise.models import Model


class UserAppConfig(Model):
    """
    A model to store `per app` config for users
    """
    id = fields.IntField(pk=True)
    user_id = fields.ForeignKeyField("models.User", related_name="configs")
    app = fields.CharField(max_length=50)
    config = fields.TextField()

    class Meta:
        unique_together = ('user_id', 'app')

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return self.__str__()
