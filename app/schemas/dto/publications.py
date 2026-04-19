import datetime as dt
from uuid import UUID

from pydantic import Field

from app.core.utils import utcnow
from app.schemas.base import EmptyBaseSchema


class UserPublicationDto(EmptyBaseSchema):
    id: UUID
    user_id: UUID
    text: str
    created_at: dt.datetime
    updated_at: dt.datetime
    is_draft: bool


class UserPublicationCreateSchema(EmptyBaseSchema):
    user_id: UUID
    created_at: dt.datetime = Field(default_factory=utcnow)
    text: str
    is_draft: bool = False


class UserPublicationUpdateSchema(EmptyBaseSchema):
    text: str | None
    updated_at: dt.datetime | None = Field(default_factory=utcnow)
    is_draft: bool | None = None
