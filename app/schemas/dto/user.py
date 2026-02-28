import datetime as dt
from uuid import UUID

from pydantic import Field

from app.core.consts import STRING_COLUMN_255
from app.schemas.base import EmptyBaseSchema
from app.schemas.types import NotEmptyString


class UserDto(EmptyBaseSchema):
    id: UUID
    first_name: str = Field()
    second_name: str
    birthdate: str
    biography: str
    city: str
    password: str
    created_at: dt.datetime


class UserCreateSchema(EmptyBaseSchema):
    first_name: NotEmptyString = Field(..., max_length=STRING_COLUMN_255)
    second_name: NotEmptyString = Field(..., max_length=STRING_COLUMN_255)
    birthdate: dt.date
    biography: str | None = None
    city: str | None = None
    password: NotEmptyString
    created_at: dt.datetime


class UserUpdateSchema(EmptyBaseSchema):
    first_name: NotEmptyString | None = Field(None, max_length=STRING_COLUMN_255)
    second_name: NotEmptyString | None = Field(None, max_length=STRING_COLUMN_255)
    birthdate: dt.date | None = None
    biography: str | None = None
    city: str | None = None
