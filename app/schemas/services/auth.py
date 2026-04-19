from uuid import UUID

from app.core.enums import ScopeType
from app.schemas.base import EmptyBaseSchema


class AuthTokenInfo(EmptyBaseSchema):
    alg: str
    public_key: str | None = None
    token_type: str | None = None


class UserData(EmptyBaseSchema):
    sub: UUID
    scope: ScopeType
