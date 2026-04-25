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


class EventTypes(StrEnum):
    ADD_FRIEND = "add_new_friend"
    REMOVE_FRIEND = "remove_friend"
    ADD_USER_PUBLICATION = "add_user_publication"
    UPDATE_USER_PUBLICATION = "update_user_publication"
    REMOVE_USER_PUBLICATION = "remove_user_publication"
