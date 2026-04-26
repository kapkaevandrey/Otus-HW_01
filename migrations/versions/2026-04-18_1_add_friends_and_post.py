"""1_add_friends_and_post

Revision ID: 9da5d40cf4e2
Revises: 1780b9511ed8
Create Date: 2026-04-18 12:46:32.661317

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '9da5d40cf4e2'
down_revision = '1780b9511ed8'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE users_publications (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL,
        text TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        is_draft BOOLEAN NOT NULL DEFAULT false,
        CONSTRAINT fk_user_publication
            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
    );
    """)
    op.execute("""
    CREATE INDEX idx_users_publications_user_id_created_at
    ON users_publications (user_id, created_at DESC);
    """)
    op.execute("""
    CREATE TABLE users_friends (
        user_id UUID,
        friend_id UUID,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT pk_users_friends PRIMARY KEY (user_id, friend_id),
        CONSTRAINT fk_users_friends_user
            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE,
        CONSTRAINT fk_users_friends_friend
            FOREIGN KEY (friend_id)
            REFERENCES users(id)
            ON DELETE CASCADE
    );
    """)


def downgrade():
    op.execute("""DROP INDEX idx_users_publications_user_id_created_at""")
    op.execute("""DROP TABLE users_friends""")
    op.execute("""DROP TABLE users_publications""")
