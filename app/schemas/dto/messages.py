import datetime as dt
from uuid import UUID, uuid4

from pydantic import Field

from app.core.utils import utcnow
from app.schemas.base import EmptyBaseSchema


class MessageDto(EmptyBaseSchema):
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    sent_at: dt.datetime
    updated_at: dt.datetime | None
    text: str


class MessageCreateSchema(EmptyBaseSchema):
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    sender_id: UUID
    sent_at: dt.datetime = Field(default_factory=utcnow)
    updated_at: dt.datetime | None = None
    text: str


class MessageUpdateSchema(EmptyBaseSchema):
    text: str
    updated_at: dt.datetime
