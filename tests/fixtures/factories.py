from collections.abc import Callable

import pytest
from starlette.websockets import WebSocket, WebSocketState

from .mock_types import MockWebSocket


@pytest.fixture
def websocket_factory() -> Callable[..., list[WebSocket]]:
    def create_websockets(
        amounts: int,
        client_state: WebSocketState = WebSocketState.CONNECTING,
        app_state: WebSocketState = WebSocketState.CONNECTING,
    ) -> list[WebSocket]:
        if amounts <= 0:
            raise ValueError("Amount must be positive")
        sockets = []
        for _ in range(amounts):
            socket = MockWebSocket(
                scope={"type": "websocket"},
                receive=MockWebSocket.fake_receive_connect,
                send=MockWebSocket.fake_send,
            )
            socket.client_state = client_state
            socket.application_state = app_state
            sockets.append(socket)
        return sockets

    return create_websockets
