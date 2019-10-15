"""Add user config column

Revision ID: 8fde2177cffa
Revises: 79b92270391a
Create Date: 2019-09-23 21:22:36.156479

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import table
import json

# revision identifiers, used by Alembic.
revision = "8fde2177cffa"
down_revision = "79b92270391a"
branch_labels = None
depends_on = None

_DEFAULT_CONFIG = {
    "weekly-playlist-update": {"enabled": True},
    "liked-sorted-yearly": {"enabled": False, "mode": "current", "data": None},
}


def upgrade():
    op.add_column(
        "user",
        sa.Column("config", sa.JSON(), server_default=json.dumps(_DEFAULT_CONFIG)),
    )


def downgrade():
    op.drop_column("user", "config")
