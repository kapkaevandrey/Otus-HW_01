import datetime as dt
from uuid import UUID

from app.schemas.base import EmptyBaseSchema


class MessageDto(EmptyBaseSchema):
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    sent_at: dt.datetime
    updated_at: dt.datetime | None
    text: str


class MessageCreateSchema(EmptyBaseSchema):
    conversation_id: UUID
    sender_id: UUID
    text: str


class MessageUpdateSchema(EmptyBaseSchema):
    text: str
    updated_at: dt.datetime
