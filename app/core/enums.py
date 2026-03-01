from enum import StrEnum


class UserType(StrEnum):
    USER = "user"


class ScopeType(StrEnum):
    ACCESS = "access"


class Tables(StrEnum):
    users = "users"
    user_tokens = "user_tokens"
