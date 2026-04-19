from enum import StrEnum


class UserType(StrEnum):
    USER = "user"


class ScopeType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class Tables(StrEnum):
    users = "users"
    users_friends = "users_friends"
    users_publications = "users_publications"
