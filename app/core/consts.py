import re
from http import HTTPStatus

from app.core.enums import WebSocketStatusCodes


STRING_COLUMN_255 = 255
POST_MAX_LENGTH = 10_000

PASSWORD_REGEX = re.compile(r"^(?=.*[A-Z])(?=.*\d)(?=.*[!-/:-@[-`{-~])[A-Za-z0-9!-/:-@[-`{-~]{8,255}$")


HTTP_STATUS_TO_WS_STATUS_MAP: dict[HTTPStatus | int, WebSocketStatusCodes] = {
    HTTPStatus.BAD_REQUEST: WebSocketStatusCodes.BAD_GATEWAY,
    HTTPStatus.UNAUTHORIZED: WebSocketStatusCodes.POLICY_VIOLATION,
    HTTPStatus.FORBIDDEN: WebSocketStatusCodes.POLICY_VIOLATION,
    HTTPStatus.NOT_FOUND: WebSocketStatusCodes.CLOSE_UNSUPPORTED,
    HTTPStatus.CONFLICT: WebSocketStatusCodes.UNSUPPORTED_PAYLOAD,
    HTTPStatus.UNPROCESSABLE_ENTITY: WebSocketStatusCodes.UNSUPPORTED_PAYLOAD,
}
