"""1_add_event_outbox

Revision ID: 5c050e72e78e
Revises: 6a6bd84828ec
Create Date: 2026-05-10 19:11:44.182592

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5c050e72e78e'
down_revision = '6a6bd84828ec'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE events_outbox (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        event_type VARCHAR(255) NOT NULL,
        properties JSONB NOT NULL
    );
    """)
    op.execute("""
    CREATE INDEX idx_events_outbox_created_at
    ON events_outbox (created_at);
    """)


def downgrade():
    op.execute("""DROP INDEX IF EXISTS idx_events_outbox_created_at""")
    op.execute("""DROP TABLE IF EXISTS events_outbox""")
