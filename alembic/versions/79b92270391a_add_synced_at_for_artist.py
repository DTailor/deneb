"""add synced_at for artist

Revision ID: 79b92270391a
Revises: 30f786bc9314
Create Date: 2019-09-16 00:00:45.910344

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision = '79b92270391a'
down_revision = '30f786bc9314'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "artist", sa.Column("synced_at", sa.DateTime, server_default=func.now())
    )

def downgrade():
    op.drop_column("artist", "synced_at")
