import datetime as dt
import uuid
from uuid import UUID

from pydantic import Field

from app.core.consts import STRING_COLUMN_255
from app.core.enums import ConversationTypes
from app.core.utils import utcnow
from app.schemas.base import EmptyBaseSchema
from app.schemas.types import NotEmptyString


class ConversationDto(EmptyBaseSchema):
    id: UUID
    type: ConversationTypes
    created_by: UUID
    title: str | None
    peer_low_id: UUID | None
    peer_high_id: UUID | None
    created_at: dt.datetime


class ConversationCreateSchema(EmptyBaseSchema):
    id: UUID = Field(default_factory=uuid.uuid4)
    type: ConversationTypes
    created_by: UUID
    title: NotEmptyString | None = Field(None, max_length=STRING_COLUMN_255)
    peer_low_id: UUID | None
    peer_high_id: UUID | None
    created_at: dt.datetime = Field(default_factory=utcnow)


class ConversationUpdateSchema(EmptyBaseSchema):
    title: NotEmptyString | None = Field(None, max_length=STRING_COLUMN_255)


class ConversationParticipantsDto(EmptyBaseSchema):
    conversation_id: UUID
    user_id: UUID


class ConversationParticipantsCreateSchema(EmptyBaseSchema):
    conversation_id: UUID
    user_id: UUID


class ConversationParticipantsUpdateSchema(EmptyBaseSchema):
    """Update operation not implemented"""
