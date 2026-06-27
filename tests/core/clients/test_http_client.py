from __future__ import annotations

from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest

from app.core.clients.http import BaseHttpClient, ChatServiceClient, HttpClientResponse
from app.exceptions import BaseClientError


@pytest.fixture
def http_client():
    client = BaseHttpClient(base_url="http://chat-service", raise_on_error=False)
    yield client


def _make_httpx_response(
    *,
    status: int = HTTPStatus.OK,
    json_data: dict | None = None,
    text: str = "",
    method: str = "GET",
    url: str = "http://chat-service/api/v1/test",
) -> httpx.Response:
    request = httpx.Request(method, url)
    if json_data is not None:
        return httpx.Response(status, json=json_data, request=request)
    return httpx.Response(status, text=text, request=request)


async def test_request_success(http_client):
    mock_client = AsyncMock()
    mock_client.request.return_value = _make_httpx_response(json_data={"ok": True})
    http_client._client = mock_client

    response = await http_client.request("GET", "/api/v1/test")

    assert isinstance(response, HttpClientResponse)
    assert response.is_success is True
    assert response.is_json is True
    assert response.json_data == {"ok": True}
    assert response.request.method == "GET"
    assert response.request.url == "http://chat-service/api/v1/test"


async def test_request_http_error_raises():
    client = BaseHttpClient(base_url="http://chat-service", raise_on_error=True)
    mock_client = AsyncMock()
    mock_client.request.return_value = _make_httpx_response(
        status=HTTPStatus.NOT_FOUND,
        json_data={"detail": {"message": "Dialog not exists", "details": {"id": "1"}}},
        method="GET",
    )
    client._client = mock_client

    with pytest.raises(BaseClientError) as exc_info:
        await client.request("GET", "/api/v1/dialog/1/list")

    error = exc_info.value
    assert error.client_name == "base_http"
    assert error.status == HTTPStatus.NOT_FOUND
    assert error.error_message == "Dialog not exists"
    assert error.error_details["method"] == "GET"


async def test_request_transport_error_raises():
    client = BaseHttpClient(base_url="http://chat-service")
    mock_client = AsyncMock()
    mock_client.request.side_effect = httpx.ConnectError("connection refused", request=MagicMock())
    client._client = mock_client

    with pytest.raises(BaseClientError) as exc_info:
        await client.request("GET", "/api/v1/test")

    assert exc_info.value.client_name == "base_http"
    assert exc_info.value.status == HTTPStatus.BAD_GATEWAY


async def test_chat_service_client_send_message():
    client = ChatServiceClient(base_url="http://chat-service", raise_on_error=False)
    mock_client = AsyncMock()
    message_id = uuid4()
    conversation_id = uuid4()
    sender_id = uuid4()
    mock_client.request.return_value = _make_httpx_response(
        method="POST",
        url="http://chat-service/api/v1/dialog/123/send",
        json_data={
            "message_id": str(message_id),
            "conversation_id": str(conversation_id),
            "sender_id": str(sender_id),
            "conversation_type": "direct",
        },
    )
    client._client = mock_client

    response = await client.send_message(
        user_id=uuid4(),
        text="hello",
        authorization="Bearer token",
        request_id="req-1",
    )

    assert response.is_success is True
    call_kwargs = mock_client.request.call_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer token"
    from app.core.request_context import REQUEST_ID_HEADER

    assert call_kwargs["headers"][REQUEST_ID_HEADER] == "req-1"
    assert call_kwargs["json"] == {"text": "hello"}

    parsed = client.parse_send_message(response)
    assert parsed.message_id == message_id
    assert parsed.conversation_type == "direct"
