"""Add user config(per app) table

Revision ID: 8fde2177cffa
Revises: 79b92270391a
Create Date: 2019-09-23 21:22:36.156479

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import table

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

    op.create_table(
        "user_app_config",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE")),
        sa.Column("app", sa.String(50)),
        sa.Column("config", sa.JSON()),
    )
    op.create_index("user_app_config_index_app", "user_app_config", ["app"])
    op.create_unique_constraint(
        "user_app_config_unique_user_id_app", "user_app_config", ["user_id", "app"]
    )
    conn = op.get_bind()
    res = conn.execute(
        sa.text(
            """
                select id from "user";
            """
        )
    )
    user_config_table = table(
        "user_app_config",
        sa.column("user_id", sa.Integer),
        sa.column("app", sa.String),
        sa.column("config", sa.JSON),
    )

    user_ids = res.fetchall()
    user_configs_bulk = []
    for (user_id,) in user_ids:
        for app, config in _DEFAULT_CONFIG.items():
            user_configs_bulk.append({"user_id": user_id, "app": app, "config": config})

    op.bulk_insert(user_config_table, user_configs_bulk)


def downgrade():
    op.drop_table("user_app_config")
