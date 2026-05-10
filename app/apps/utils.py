from fastapi import HTTPException, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.schemas.services import BaseServiceResponse


def collect_error_data_from_service_response(response: BaseServiceResponse) -> dict | None:
    if response.is_success:
        return None
    return {
        "error": {
            "code": response.status,
            "message": response.error_message,
            "details": response.error_details,
        }
    }


async def read_bytes_from_websocket(
    websocket: WebSocket,
) -> bytes | None:
    message = None
    data = await websocket.receive()
    if data["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(data.get("code", 1000))
    if data.get("bytes") is not None:
        message = data["bytes"]
    elif data.get("text") is not None:
        message = data["text"].encode("utf-8")
    return message


def raise_http_exception_from_service_response(response: BaseServiceResponse, retry_after: int = 15) -> None:
    if response.is_success:
        return
    headers = {"Retry-After": retry_after} if response.status >= 500 else {}
    raise HTTPException(
        status_code=response.status,
        detail={
            "message": response.error_message,
            "details": response.error_details,
            "headers": headers,
        },
    )
