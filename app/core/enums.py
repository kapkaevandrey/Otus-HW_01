from enum import IntEnum, StrEnum


class UserType(StrEnum):
    USER = "user"


class ScopeType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class ConversationTypes(StrEnum):
    DIRECT = "direct"
    GROUP = "group"


class Tables(StrEnum):
    users = "users"
    users_friends = "users_friends"
    users_publications = "users_publications"
    conversations = "conversations"
    conversation_participants = "conversation_participants"
    messages = "messages"
    events_outbox = "events_outbox"


class EventTypes(StrEnum):
    ADD_FRIEND = "add_new_friend"
    REMOVE_FRIEND = "remove_friend"
    ADD_USER_PUBLICATION = "add_user_publication"
    SEND_NEW_POST_FOR_FRIENDS = "send_new_post_for_friends"
    UPDATE_USER_PUBLICATION = "update_user_publication"
    REMOVE_USER_PUBLICATION = "remove_user_publication"


class WebSocketStatusCodes(IntEnum):
    """
    RFC-6455
    https://datatracker.ietf.org/doc/html/rfc6455#section-7.4
    """

    CLOSE_NORMAL = 1000
    CLOSE_GOING_AWAY = 1001
    CLOSE_PROTOCOL_ERROR = 1002
    CLOSE_UNSUPPORTED = 1003
    UNSUPPORTED_PAYLOAD = 1007
    POLICY_VIOLATION = 1008
    CLOSE_TOO_LARGE = 1009
    MANDATORY_EXTENSION = 1010
    SERVER_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN_LATTER = 1013
    BAD_GATEWAY = 1014
    TLS_HANDSHAKE_FAILURE = 1015
