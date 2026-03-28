# alembic: no_transaction
"""1_add_gin_indexes

Revision ID: 1780b9511ed8
Revises: 0d8fee3fd7bb
Create Date: 2026-03-28 14:25:22.575132

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '1780b9511ed8'
down_revision = '0d8fee3fd7bb'
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_first_name_trgm ON users USING GIN(first_name gin_trgm_ops);"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_second_name_trgm ON users USING GIN(second_name gin_trgm_ops);"
        )

def downgrade():
    op.execute("DROP INDEX idx_first_name_trgm;")
    op.execute("DROP INDEX idx_second_name_trgm;")