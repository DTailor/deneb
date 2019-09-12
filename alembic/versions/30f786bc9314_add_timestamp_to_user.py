"""Add timestamp to user

Revision ID: 30f786bc9314
Revises: d00285e9d305
Create Date: 2019-07-16 21:38:26.715520

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import func
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = "30f786bc9314"
down_revision = "d00285e9d305"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user", sa.Column("created_at", sa.DateTime, server_default=func.now())
    )
    op.add_column(
        "user",
        sa.Column("updated_at", sa.DateTime, server_default=func.now(), nullable=True),
    )
    conn = op.get_bind()
    conn.execute(
        text(
            """
            CREATE FUNCTION update_updated_at_column() RETURNS trigger
                LANGUAGE plpgsql
                AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$;

            CREATE TRIGGER user_updated_at BEFORE UPDATE ON "user" FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
            """
        )
    )


def downgrade():
    op.drop_column("user", "created_at")
    op.drop_column("user", "updated_at")
    conn = op.get_bind()
    conn.execute(
        text(
            """
            DROP TRIGGER IF EXISTS user_updated_at ON "user";
            DROP FUNCTION IF EXISTS update_updated_at_column;
            """
        )
    )
