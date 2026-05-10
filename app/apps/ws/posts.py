from logging import getLogger

from fastapi import APIRouter, Depends, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.config import auth_settings
from app.core.consts import HTTP_STATUS_TO_WS_STATUS_MAP
from app.core.containers import Context, get_context
from app.core.enums import WebSocketStatusCodes
from app.core.services import AuthService
from app.schemas.services import AuthCheckTokenData


feed_ws_router = APIRouter()

logger = getLogger(__name__)


@feed_ws_router.websocket("/post/feed/posted")
async def feed_socket(
    websocket: WebSocket,
    context: Context = Depends(get_context),
) -> None:
    headers = dict(websocket.headers.items())
    service = AuthService(context=context)
    auth_response = await service.get_user_auth_token_data_from_headers(
        headers=headers,
        auth_data=AuthCheckTokenData(
            alg=auth_settings.JWT_ALG,
            header_key=auth_settings.AUTH_HEADER_KEY,
            public_key=auth_settings.JWT_PUB_KEY,
            token_type=auth_settings.AUTH_TOKEN_TYPE,
        ),
    )
    error_reason, error_details, error_code = "", {}, 200
    if not auth_response.is_success:
        error_reason = f"Authentication failed. Reason: {auth_response.error_message}"
        error_details = {"details": auth_response.error_details}
        error_code = auth_response.status
    if error_reason:
        logger.info(error_reason, extra=error_details)
        socket_code = HTTP_STATUS_TO_WS_STATUS_MAP.get(error_code, WebSocketStatusCodes.CLOSE_NORMAL)
        await context.socket_manager.disconnect(
            websocket,
            code=socket_code,
            reason=error_reason,
        )
        return
    user_data = auth_response.result
    if not await context.socket_manager.connect_user(str(user_data.sub), websocket):
        return
    close_code = WebSocketStatusCodes.CLOSE_NORMAL
    close_reason = "Client disconnected"
    try:
        while True:
            while True:
                message = await websocket.receive_text()
                logger.info("Received message: %s", message)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception as exc:
        logger.exception("Unexpected error handling websocket connection", exc_info=exc)
        close_code = WebSocketStatusCodes.SERVER_ERROR
        close_reason = "Internal server error"
    finally:
        await context.socket_manager.disconnect_user(
            str(user_data.sub), websocket, code=close_code, reason=close_reason
        )
