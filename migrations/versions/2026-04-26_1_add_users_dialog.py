"""1_add_users_dialog

Revision ID: 6a6bd84828ec
Revises: 9da5d40cf4e2
Create Date: 2026-04-26 19:51:31.493151

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '6a6bd84828ec'
down_revision = '9da5d40cf4e2'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE conversations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        type VARCHAR(16) NOT NULL,
        created_by UUID NOT NULL,
        title VARCHAR(255) NULL,
        peer_low_id UUID NULL,
        peer_high_id UUID NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        
        CONSTRAINT chk_conversations_type CHECK (type IN ('direct', 'group')),
        CONSTRAINT chk_direct_peers_order CHECK (
            peer_low_id IS NULL OR peer_high_id IS NULL OR peer_high_id > peer_low_id
        ),
        CONSTRAINT chk_direct_peers CHECK (
            (type = 'direct' AND peer_low_id IS NOT NULL AND peer_high_id IS NOT NULL)
            OR
            (type = 'group' AND peer_high_id IS NULL AND peer_low_id IS NULL)
        )
    );
    """)
    op.execute("""
    CREATE UNIQUE INDEX ux_conversation_direct_pair 
    ON conversations (peer_low_id, peer_high_id)
    WHERE type = 'direct';
    """)
    op.execute("""
    CREATE TABLE conversation_participants (
        conversation_id UUID NOT NULL,
        user_id UUID NOT NULL,
        CONSTRAINT pk_conversation_participants PRIMARY KEY (user_id, conversation_id),
        CONSTRAINT fk_user_conversation_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        CONSTRAINT fk_conversation_id FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    );
    """)
    op.execute("""
    CREATE TABLE messages (
        conversation_id UUID NOT NULL,
        id UUID NOT NULL DEFAULT gen_random_uuid(),
        sender_id UUID NOT NULL,
        sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NULL,
        text TEXT NOT NULL,
        CONSTRAINT pk_messages PRIMARY KEY (conversation_id, id)
    );
    """)
    op.execute("""
    CREATE INDEX idx_conversation_participants_conversation_id
    ON conversation_participants (conversation_id);
    """)
    op.execute("""
    CREATE INDEX idx_messages_conversation_sent_at
    ON messages (conversation_id, sent_at DESC, id DESC);
    """)
    with op.get_context().autocommit_block():
        op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'citus') THEN
                CREATE EXTENSION IF NOT EXISTS citus;
            END IF;
        END
        $$;
        """)
        op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'citus')
               AND NOT EXISTS (
                   SELECT 1
                   FROM pg_dist_partition
                   WHERE logicalrelid = 'messages'::regclass
               ) THEN
                PERFORM create_distributed_table('messages', 'conversation_id');
            END IF;
        END
        $$;
        """)



def downgrade():
    op.execute("""DROP INDEX idx_messages_conversation_sent_at;""")
    op.execute("""DROP INDEX idx_conversation_participants_conversation_id;""")
    op.execute("""DROP TABLE messages;""")
    op.execute("""DROP TABLE conversation_participants;""")
    op.execute("""DROP INDEX ux_conversation_direct_pair;""")
    op.execute("""DROP TABLE conversations;""")
