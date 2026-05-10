import asyncio
import logging
import uuid

import pytest
from starlette.websockets import WebSocketState


async def test_disconnected_socket_client_disconnected(
    context,
    websocket_factory,
    caplog: pytest.LogCaptureFixture,
):
    sockets = websocket_factory(1, WebSocketState.DISCONNECTED)
    socket_key = id(sockets[0])
    await context.socket_manager.connect(sockets[0])
    assert context.socket_manager.active_connections.get(socket_key) is not None
    await context.socket_manager.disconnect(sockets[0])
    assert context.socket_manager.active_connections.get(socket_key) is None


async def test_disconnected_socket_client(
    context,
    websocket_factory,
    caplog: pytest.LogCaptureFixture,
):
    sockets = websocket_factory(1, WebSocketState.CONNECTED)
    socket_key = id(sockets[0])
    caplog.set_level(logging.INFO)
    await context.socket_manager.connect(sockets[0])
    assert context.socket_manager.active_connections.get(socket_key) is not None
    await context.socket_manager.disconnect(sockets[0])
    assert context.socket_manager.active_connections.get(socket_key) is None
    assert f"Disconnected Socket: {socket_key} with reason: None" in caplog.text


async def test_disconnected_socket_client_connecting_status(
    context,
    websocket_factory,
    caplog: pytest.LogCaptureFixture,
):
    sockets = websocket_factory(1)
    socket_key = id(sockets[0])
    caplog.set_level(logging.INFO)
    await context.socket_manager.connect(sockets[0])
    assert context.socket_manager.active_connections.get(socket_key) is not None
    await context.socket_manager.disconnect(sockets[0])
    assert context.socket_manager.active_connections.get(socket_key) is None
    assert f"Disconnected Socket: {socket_key} with reason: None" in caplog.text


async def test_websocket_send_data(
    context,
    websocket_factory,
):
    sockets = websocket_factory(1)
    await context.socket_manager.connect(sockets[0])
    await context.socket_manager.send_personal_message("my_message", sockets[0])
    await context.socket_manager.send_personal_json({"key": "value"}, sockets[0])


async def test_start_stop_websocket_manager(
    context,
    websocket_factory,
):
    assert context.socket_manager._cleanup_task is None
    await context.socket_manager.start()
    assert isinstance(context.socket_manager._cleanup_task, asyncio.Task)
    await context.socket_manager.stop()
    assert context.socket_manager._cleanup_task is None


async def test_websocket_manager_received_json_timeout(
    context,
    websocket_factory,
):
    async def fake_receive_json(*args, **kwargs):
        await asyncio.sleep(5)
        return {"key": "value"}

    sockets = websocket_factory(1)
    sockets[0].receive_json = fake_receive_json
    await context.socket_manager.connect(sockets[0])
    result = await context.socket_manager.received_json(sockets[0], timeout=0.5)
    assert result is None


async def test_websocket_manager_received_json(
    context,
    websocket_factory,
):
    data = {"key": "value"}

    async def fake_receive_json(*args, **kwargs):
        await asyncio.sleep(0.1)
        return data

    sockets = websocket_factory(1)
    sockets[0].receive_json = fake_receive_json
    await context.socket_manager.connect(sockets[0])
    result = await context.socket_manager.received_json(sockets[0], timeout=0.5)
    assert result == data


async def test_connect_device_application(
    context,
    websocket_factory,
):
    sockets = websocket_factory(1)
    user_id = uuid.uuid4().hex
    await context.socket_manager.connect_user(user_id, sockets[0])
    socket_key = context.socket_manager.websocket_key(sockets[0])
    assert len(context.socket_manager.active_connections) == 1
    assert len(context.socket_manager._ws_to_user_id_map) == 1
    assert context.socket_manager.active_connections_user_map[user_id] == socket_key
    user_id_val = context.socket_manager._ws_to_user_id_map[socket_key]
    assert user_id_val == user_id
    assert socket_key in context.socket_manager.active_connections
    assert socket_key in context.socket_manager._ws_to_user_id_map


async def test_connect_device_application_reject_duplicate_device_connection(
    context,
    websocket_factory,
):
    async def fake_close(*args, **kwargs):
        close_calls.append(kwargs)

    user_id = uuid.uuid4().hex
    sockets = websocket_factory(2)
    first_connected = await context.socket_manager.connect_user(user_id, sockets[0])
    first_socket_key = context.socket_manager.websocket_key(sockets[0])
    close_calls = []
    sockets[1].close = fake_close
    second_connected = await context.socket_manager.connect_user(user_id, sockets[1])
    assert first_connected is True
    assert second_connected is False
    assert len(context.socket_manager.active_connections) == 1
    assert context.socket_manager.active_connections_user_map[user_id] == first_socket_key
    assert context.socket_manager.active_connections.get(first_socket_key).ws is sockets[0]
    assert close_calls
    assert close_calls[0]["code"] == 1008
    assert close_calls[0]["reason"] == "Connection for this user/device already exists"


async def test_disconnect_user_device_without_ssocket(
    context,
    websocket_factory,
):
    user_ids = [uuid.uuid4().hex for _ in range(5)]
    user_sockets = websocket_factory(5)
    for i, s in enumerate(user_sockets):
        await context.socket_manager.connect_user(user_ids[i], s)
    await context.socket_manager.disconnect_user(user_ids[0], None)
    assert len(context.socket_manager.active_connections) == len(user_sockets)
    assert len(context.socket_manager._ws_to_user_id_map) == len(user_sockets)
    assert len(context.socket_manager.active_connections_user_map) == len(user_sockets)


async def test_cleanup_not_active_connections(
    context,
    websocket_factory,
):
    items = 5
    user_ids = [uuid.uuid4().hex for _ in range(items)]
    user_sockets = websocket_factory(items)
    for i, s in enumerate(user_sockets):
        await context.socket_manager.connect_user(user_ids[i], s)
    for s in user_sockets:
        s.client_state = WebSocketState.DISCONNECTED
    await context.socket_manager.cleanup_connections(max_retries=2, unless=False, delay=0.5)
    assert len(context.socket_manager.active_connections) == 0
    assert len(context.socket_manager._ws_to_user_id_map) == 0
    assert len(context.socket_manager.active_connections_user_map) == 0


async def test_cleanup_not_active_connections_many_tries(
    context,
    websocket_factory,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_clean_up_connections(*aegs, **kwargs):
        raise RuntimeError()

    items = 5
    user_ids = [uuid.uuid4().hex for _ in range(items)]
    user_sockets = websocket_factory(items)
    for _ in range(items):
        await context.socket_manager.connect_user(user_ids[_], user_sockets[_])
    for s in user_sockets:
        s.client_state = WebSocketState.DISCONNECTED
    monkeypatch.setattr(context.socket_manager, "_cleanup_connections", fake_clean_up_connections)
    with pytest.raises(RuntimeError):
        await context.socket_manager.cleanup_connections(max_retries=2, unless=True, delay=0.5, retry_delay=0.5)


async def test_concurrent_connections(
    context,
    websocket_factory,
):
    items = 500
    user_id = uuid.uuid4().hex
    user_sockets = websocket_factory(items)
    tasks = [context.socket_manager.connect_user(user_id, s) for i, s in enumerate(user_sockets)]
    results = await asyncio.gather(*tasks)
    assert sum(results) == 1
