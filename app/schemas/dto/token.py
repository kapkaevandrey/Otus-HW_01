import datetime as dt
from uuid import UUID

from app.core.enums import ScopeType, UserType
from app.schemas.base import EmptyBaseSchema


class UserTokenDto(EmptyBaseSchema):
    user_id: UUID
    token: UUID
    scope: ScopeType
    user_type: UserType
    created_at: dt.datetime


class UserTokenCreateSchema(EmptyBaseSchema):
    user_id: UUID
    token: UUID
    scope: ScopeType
    user_type: UserType


class UserTokenUpdateSchema(EmptyBaseSchema):
    """Not Implemented"""

    pass
