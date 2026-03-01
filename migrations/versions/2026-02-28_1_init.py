"""1_init

Revision ID: 0d8fee3fd7bb
Revises: 
Create Date: 2026-02-28 21:19:43.885136

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0d8fee3fd7bb'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        first_name VARCHAR(255) NOT NULL,
        second_name VARCHAR(255) NOT NULL,
        birthdate DATE NOT NULL,
        biography TEXT,
        city VARCHAR(255),
        password VARCHAR(255) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)
    op.execute("""
    CREATE TABLE user_tokens (
        user_id UUID NOT NULL,
        token UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        scope VARCHAR(255),
        user_type VARCHAR(255),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_user
            FOREIGN KEY(user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
    );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_tokens;")
    op.execute("DROP TABLE IF EXISTS users;")
