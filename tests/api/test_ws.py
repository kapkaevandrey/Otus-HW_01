from uuid import uuid4

import jwt
import pytest
from starlette.websockets import WebSocketDisconnect

from app.config import auth_settings
from app.core.enums import ScopeType, WebSocketStatusCodes
from app.schemas.services import UserTokenData
from app.server import app


async def test_ws_connect_not_authorized(ws_client, context):
    url = app.url_path_for("feed_socket")
    with (
        pytest.raises(WebSocketDisconnect) as exc,
        ws_client.websocket_connect(url) as websocket,
    ):
        websocket.send_json({"app_type": "app_type"})
    assert exc.value.code == WebSocketStatusCodes.POLICY_VIOLATION


@pytest.mark.parametrize(
    "token",
    [
        "fake",
        "Bar bar",
        f"{auth_settings.AUTH_TOKEN_TYPE}",
        f"{auth_settings.AUTH_TOKEN_TYPE} fake",
        f"{auth_settings.AUTH_TOKEN_TYPE} asdf.asdf.asdf",
        f"{auth_settings.AUTH_TOKEN_TYPE} " + jwt.encode(payload={"key": "value"}, key="key", algorithm="HS256"),
    ],
)
async def test_ws_connect_not_authorized_bad_token(ws_client, context, token):
    url = app.url_path_for("feed_socket")
    with (
        pytest.raises(WebSocketDisconnect) as exc,
        ws_client.websocket_connect(
            url,
            headers={auth_settings.AUTH_HEADER_KEY: f"{token}"},
        ) as websocket,
    ):
        websocket.receive_text()
    assert exc.value.code == WebSocketStatusCodes.POLICY_VIOLATION


async def test_ws_connect(
    ws_client,
    context,
):
    url = app.url_path_for("feed_socket")
    device_data = UserTokenData(sub=uuid4(), scope=ScopeType.ACCESS)
    token = jwt.encode(payload=device_data.model_dump(mode="json"), key=auth_settings.JWT_PUB_KEY, algorithm="HS256")
    with ws_client.websocket_connect(
        url,
        headers={auth_settings.AUTH_HEADER_KEY: f"{auth_settings.AUTH_TOKEN_TYPE} {token}"},
    ) as websocket:
        websocket.send_json({"app_type": "app_type"})
