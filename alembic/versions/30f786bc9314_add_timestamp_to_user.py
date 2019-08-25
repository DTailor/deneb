"""Add timestamp to user

Revision ID: 30f786bc9314
Revises: d00285e9d305
Create Date: 2019-07-16 21:38:26.715520

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "30f786bc9314"
down_revision = "d00285e9d305"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user", sa.Column("created_at", sa.DateTime, default=sa.func.now()))
    op.add_column(
        "user", sa.Column("updated_at", sa.DateTime, onupdate=sa.func.sysdate())
    )


def downgrade():
    op.drop_column("user", "created_at")
    op.drop_column("user", "updated_at")
