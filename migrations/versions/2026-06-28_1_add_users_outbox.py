"""add_users_outbox

Revision ID: a1b2c3d4e5f6
Revises: 5c050e72e78e
Create Date: 2026-06-28 12:00:00.000000

"""

from alembic import op


revision = "a1b2c3d4e5f6"
down_revision = "5c050e72e78e"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE users_outbox (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        action VARCHAR(32) NOT NULL,
        data JSONB NOT NULL
    );
    """)
    op.execute("""
    CREATE INDEX idx_users_outbox_created_at ON users_outbox (created_at);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS users_outbox;")
