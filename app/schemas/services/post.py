import datetime as dt
from uuid import UUID

from pydantic import Field

from app.core.consts import POST_MAX_LENGTH
from app.schemas.base import EmptyBaseSchema
from app.schemas.types import NotEmptyString


class PostCreateServiceSchema(EmptyBaseSchema):
    text: NotEmptyString = Field(max_length=POST_MAX_LENGTH)


class PostUpdateServiceSchema(EmptyBaseSchema):
    id: UUID
    text: NotEmptyString = Field(max_length=POST_MAX_LENGTH)


class GetPostServiceResponseSchema(EmptyBaseSchema):
    id: UUID
    text: str
    user_id: UUID = Field(serialization_alias="author_user_id")
    created_at: dt.datetime
    updated_at: dt.datetime
