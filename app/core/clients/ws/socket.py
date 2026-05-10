import asyncio

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.schemas.services import AsyncChannelQueue


class ActiveWebSocket:
    def __init__(self, ws: WebSocket, read_queue: AsyncChannelQueue):
        self.ws = ws
        self.read_queue = read_queue
        self.sender_task = asyncio.create_task(self.ws_sender_task())

    async def ws_sender_task(self):
        try:
            while self.read_queue.is_active:
                try:
                    item = await asyncio.wait_for(self.read_queue.queue.get(), timeout=0.2)
                except TimeoutError:
                    continue
                if isinstance(item, bytes):
                    await self.ws.send_bytes(item)
                else:
                    await self.ws.send_json(item)
        except asyncio.CancelledError:
            raise
        except WebSocketDisconnect:
            pass
        finally:
            self.read_queue.is_active = False

    async def stop(self):
        self.read_queue.is_active = False
        self.sender_task.cancel()
