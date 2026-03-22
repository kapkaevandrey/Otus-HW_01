import datetime as dt
from uuid import UUID

from pydantic import Field, field_validator

from app.core.consts import PASSWORD_REGEX, STRING_COLUMN_255
from app.schemas.base import EmptyBaseSchema
from app.schemas.types import NotEmptyString


class RegisterUserData(EmptyBaseSchema):
    first_name: NotEmptyString = Field(min_length=1, max_length=STRING_COLUMN_255)
    second_name: NotEmptyString = Field(min_length=1, max_length=STRING_COLUMN_255)
    birthdate: dt.date
    biography: str | None = None
    city: str | None = None
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not PASSWORD_REGEX.fullmatch(value):
            raise ValueError("Password contains invalid characters or wrong length")
        if not any(c.isupper() for c in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one digit")
        if not any(not c.isalnum() for c in value):
            raise ValueError("Password must contain at least one special character")
        return value


class RegisterUserServiceResponse(EmptyBaseSchema):
    user_id: UUID


class LoginUserData(EmptyBaseSchema):
    id: UUID
    password: str


class RefreshUserToken(EmptyBaseSchema):
    id: UUID
    password: str


class TokenSchema(EmptyBaseSchema):
    type: str
    scope: str
    token: str
    exp: int


class AccessRefreshServiceResponse(EmptyBaseSchema):
    access_token: TokenSchema
    refresh_token: TokenSchema


class AuthUserServiceResponse(EmptyBaseSchema):
    token: UUID


class GetUserServiceResponse(EmptyBaseSchema):
    id: UUID
    first_name: str
    second_name: str
    birthdate: dt.date
    biography: str | None
    city: str | None
