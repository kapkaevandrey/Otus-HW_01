import asyncio
import json

from starlette.websockets import WebSocketDisconnect, WebSocketState

from app.core.clients.ws.socket import ActiveWebSocket
from app.schemas.services import AsyncChannelQueue


async def test_active_websocket_sender_task_sends_json(websocket_factory):
    websocket = websocket_factory(1, client_state=WebSocketState.CONNECTED)[0]
    read_queue = AsyncChannelQueue(queue=asyncio.Queue())
    active_ws = ActiveWebSocket(ws=websocket, read_queue=read_queue)
    payload = {"type": "recognition_response", "data": {"text": "hello"}}
    await read_queue.queue.put(payload)
    await asyncio.sleep(0.1)
    sent_message = websocket.sent[0]
    assert sent_message["type"] == "websocket.send"
    assert json.loads(sent_message["text"]) == payload
    await active_ws.stop()


async def test_active_websocket_sender_task_sends_bytes(websocket_factory):
    websocket = websocket_factory(1, client_state=WebSocketState.CONNECTED)[0]
    read_queue = AsyncChannelQueue(queue=asyncio.Queue())
    active_ws = ActiveWebSocket(ws=websocket, read_queue=read_queue)
    payload = b"chunk"
    await read_queue.queue.put(payload)
    await asyncio.sleep(0.1)
    sent_message = websocket.sent[0]
    assert sent_message["type"] == "websocket.send"
    assert sent_message["bytes"] == payload
    await active_ws.stop()


async def test_active_websocket_stop_disables_queue_and_cancels_task(websocket_factory):
    websocket = websocket_factory(1, client_state=WebSocketState.CONNECTED)[0]
    read_queue = AsyncChannelQueue(queue=asyncio.Queue())
    active_ws = ActiveWebSocket(ws=websocket, read_queue=read_queue)

    await active_ws.stop()
    await asyncio.sleep(0.1)
    assert read_queue.is_active is False
    assert active_ws.sender_task.cancelled() is True


async def test_active_websocket_sender_task_handles_websocket_disconnect(websocket_factory):
    websocket = websocket_factory(1, client_state=WebSocketState.CONNECTED)[0]
    read_queue = AsyncChannelQueue(queue=asyncio.Queue())
    active_ws = ActiveWebSocket(ws=websocket, read_queue=read_queue)

    async def raise_disconnect(*args, **kwargs):
        raise WebSocketDisconnect(code=1000)

    websocket.send_json = raise_disconnect
    await read_queue.queue.put({"type": "recognition_response"})
    await asyncio.sleep(0.1)
    assert active_ws.sender_task.done() is True
    assert read_queue.is_active is False
