from uuid import UUID

from app.core.enums import EventTypes
from app.schemas.dto import (
    EventActionOutboxCreateSchema,
    EventActionOutboxDto,
    EventActionOutboxUpdateSchema,
)

from .base import BaseRepository


class EventActionOutboxRepo(
    BaseRepository[EventActionOutboxDto, EventActionOutboxCreateSchema, EventActionOutboxUpdateSchema]
):
    async def create_send_post_to_all_consumers_events(
        self,
        post_id: UUID,
        author_id: UUID,
        event_type: EventTypes,
    ) -> None:
        query = """
            INSERT INTO events_outbox (event_type, properties)
            SELECT
                :event_type,
                jsonb_build_object(
                    'consumer_id', users_friends.user_id,
                    'post_id', CAST(:post_id AS TEXT)
                )
            FROM users_friends
            WHERE users_friends.friend_id = :author_id
        """
        await self.db_client.execute_stmt(
            query=query,
            params={
                "event_type": event_type,
                "post_id": str(post_id),
                "author_id": author_id,
            },
            external_session=self._session,
            need_result=False,
        )
        return None
