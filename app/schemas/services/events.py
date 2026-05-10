from uuid import UUID

from app.schemas.base import EmptyBaseSchema


class ServiceEvent(EmptyBaseSchema):
    event_type: str
    data: dict


class PostForFriendsEventSchema(EmptyBaseSchema):
    post_id: UUID
    consumer_id: UUID
