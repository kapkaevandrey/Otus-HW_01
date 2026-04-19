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
    birthdate: dt.date
    biography: str | None
    city: str | None
    password: str
    created_at: dt.datetime


class UserCreateSchema(EmptyBaseSchema):
    first_name: NotEmptyString = Field(min_length=1, max_length=STRING_COLUMN_255)
    second_name: NotEmptyString = Field(min_length=1, max_length=STRING_COLUMN_255)
    birthdate: dt.date
    biography: str | None = None
    city: str | None = None
    password: NotEmptyString = Field(min_length=1, max_length=STRING_COLUMN_255)


class UserUpdateSchema(EmptyBaseSchema):
    first_name: NotEmptyString | None = Field(None, max_length=STRING_COLUMN_255)
    second_name: NotEmptyString | None = Field(None, max_length=STRING_COLUMN_255)
    birthdate: dt.date | None = None
    biography: str | None = None
    city: str | None = None


class UserFriendDto(EmptyBaseSchema):
    user_id: UUID
    friend_id: UUID
    created_at: dt.datetime


class UserFriendCreateSchema(EmptyBaseSchema):
    user_id: UUID
    friend_id: UUID


class UserFriendUpdateSchema(EmptyBaseSchema):
    """Update operation not implemented"""
