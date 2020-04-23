"""Migrate all tables under deneb scheme

Revision ID: c5a2efda32eb
Revises: 8fde2177cffa
Create Date: 2019-10-28 20:35:25.361588

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = "c5a2efda32eb"
down_revision = "8fde2177cffa"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(
        text(
            """
                CREATE SCHEMA deneb;

                ALTER TABLE album
                 SET SCHEMA deneb;

                ALTER TABLE album_markets
                 SET SCHEMA deneb;

                ALTER TABLE artist
                 SET SCHEMA deneb;

                ALTER TABLE artist_albums
                 SET SCHEMA deneb;

                ALTER TABLE market
                 SET SCHEMA deneb;

                ALTER TABLE "user"
                 SET SCHEMA deneb;

                ALTER TABLE user_followed_artists
                 SET SCHEMA deneb;
            """
        )
    )


def downgrade():
    conn = op.get_bind()
    conn.execute(
        text(
            """
                ALTER TABLE deneb.album
                 SET SCHEMA public;

                ALTER TABLE deneb.album_markets
                 SET SCHEMA public;

                ALTER TABLE deneb.artist
                 SET SCHEMA public;

                ALTER TABLE deneb.artist_albums
                 SET SCHEMA public;

                ALTER TABLE deneb.market
                 SET SCHEMA public;

                ALTER TABLE deneb."user"
                 SET SCHEMA public;

                ALTER TABLE deneb.user_followed_artists
                 SET SCHEMA public;

                DROP SCHEMA deneb;
            """
        )
    )
