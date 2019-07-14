"""init db

Revision ID: d00285e9d305
Revises: 
Create Date: 2019-03-12 00:50:48.582099

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d00285e9d305"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "market",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(5), unique=True),
    )

    op.create_table(
        "user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("fb_id", sa.String(20), nullable=False),
        sa.Column("username", sa.Unicode(200)),
        sa.Column("market_id", sa.Integer, sa.ForeignKey("market.id")),
        sa.Column("spotify_token", sa.String(1000)),
        sa.Column("display_name", sa.String(255)),
        sa.Column("state_id", sa.String(255)),
    )

    op.create_table(
        "artist",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("spotify_id", sa.String(25), unique=True),
        sa.Column("name", sa.String(255)),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index('artist_unique_spotify_id', 'artist', ['spotify_id'])

    op.create_table(
        "album",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("spotify_id", sa.String(25), unique=True),
        sa.Column("name", sa.String(255)),
        sa.Column("type", sa.String(10)),
        sa.Column("release", sa.Date()),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index('album_unique_spotify_id', 'album', ['spotify_id'])

    op.create_table(
        "user_followed_artists",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE")),
        sa.Column("artist_id", sa.Integer, sa.ForeignKey("artist.id", ondelete="CASCADE")),
    )

    op.create_table(
        "artist_albums",
        sa.Column("album_id", sa.Integer, sa.ForeignKey("album.id", ondelete="CASCADE")),
        sa.Column("artist_id", sa.Integer, sa.ForeignKey("artist.id", ondelete="CASCADE")),
    )

    op.create_table(
        "album_markets",
        sa.Column("album_id", sa.Integer, sa.ForeignKey("album.id", ondelete="CASCADE")),
        sa.Column("market_id", sa.Integer, sa.ForeignKey("market.id", ondelete="CASCADE")),
    )


def downgrade():
    op.drop_table("user_followed_artists")
    op.drop_table("artist_albums")
    op.drop_table("album_markets")
    op.drop_table("artist")
    op.drop_table("album")
    op.drop_table("user")
    op.drop_table("market")
