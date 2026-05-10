from starlette.types import Message
from starlette.websockets import WebSocket


class MockWebSocket(WebSocket):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sent = []
        self.received = []

    async def send(self, message: Message) -> None:
        self.sent.append(message)

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        pass

    @classmethod
    async def fake_receive_connect(cls, *args, **kwargs) -> Message:
        return {"type": "websocket.connect"}

    @classmethod
    async def fake_send(cls, *args, **kwargs) -> Message:
        pass
