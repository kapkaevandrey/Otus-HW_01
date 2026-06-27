import datetime as dt
from uuid import UUID, uuid4

from pydantic import Field

from app.schemas.base import EmptyBaseSchema


class EventActionOutboxDto(EmptyBaseSchema):
    id: UUID
    created_at: dt.datetime
    event_type: str
    properties: dict


class EventActionOutboxCreateSchema(EmptyBaseSchema):
    id: UUID = Field(default_factory=uuid4)
    event_type: str
    properties: dict


class EventActionOutboxUpdateSchema(EmptyBaseSchema):
    """Updates operation not implemented"""


class UserOutboxDataSchema(EmptyBaseSchema):
    id: UUID
    first_name: str
    second_name: str
    birthdate: dt.date
    biography: str | None = None
    city: str | None = None


class UserOutboxDto(EmptyBaseSchema):
    id: UUID
    created_at: dt.datetime
    action: str
    data: dict


class UserOutboxCreateSchema(EmptyBaseSchema):
    id: UUID = Field(default_factory=uuid4)
    action: str
    data: dict


class UserOutboxUpdateSchema(EmptyBaseSchema):
    """Updates operation not implemented"""
