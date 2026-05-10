import json
from types import SimpleNamespace
from uuid import uuid4

from app.apps.consumers import WsMessagesConsumer
from app.schemas.services import InboxWsMessage


def _get_consumer_with_context(context) -> WsMessagesConsumer:
    consumer = WsMessagesConsumer(
        consumer_class=object,
        consumer_args=(),
        consumer_kwargs={},
    )
    consumer.__dict__["context"] = context
    return consumer


async def test_process_message_sends_payload_to_active_socket(context, websocket_factory):
    consumer = _get_consumer_with_context(context)
    user_id = str(uuid4())
    payload = {"postId": str(uuid4()), "postText": "new post", "author_user_id": str(uuid4())}
    socket = websocket_factory(1)[0]
    assert await context.socket_manager.connect_user(user_id, socket)

    await consumer.process_message(
        SimpleNamespace(
            value={
                "event_type": "send_new_post_for_friends",
                "send_to_user_id": user_id,
                "payload": payload,
            },
            timestamp=0,
        )
    )

    sent_message = next(message for message in reversed(socket.sent) if message["type"] == "websocket.send")
    assert json.loads(sent_message["text"]) == payload


async def test_process_message_logs_when_socket_not_found(context, caplog):
    consumer = _get_consumer_with_context(context)
    user_id = str(uuid4())

    await consumer.process_message(
        SimpleNamespace(
            value={
                "event_type": "send_new_post_for_friends",
                "send_to_user_id": user_id,
                "payload": {"postId": str(uuid4())},
            },
            timestamp=0,
        )
    )

    assert f"Active websocket for user {user_id} not found." in caplog.text


async def test_process_message_skips_invalid_payload(context):
    consumer = _get_consumer_with_context(context)
    await consumer.process_message(SimpleNamespace(value=b"invalid-json", timestamp=0))


def test_try_get_message_schema_parses_dict_string_and_bytes():
    consumer = WsMessagesConsumer(
        consumer_class=object,
        consumer_args=(),
        consumer_kwargs={},
    )
    raw = {
        "event_type": "send_new_post_for_friends",
        "send_to_user_id": str(uuid4()),
        "payload": {"postId": str(uuid4())},
    }

    parsed_from_dict = consumer.try_get_message_schema(raw)
    parsed_from_string = consumer.try_get_message_schema(json.dumps(raw))
    parsed_from_bytes = consumer.try_get_message_schema(json.dumps(raw).encode())

    assert isinstance(parsed_from_dict, InboxWsMessage)
    assert isinstance(parsed_from_string, InboxWsMessage)
    assert isinstance(parsed_from_bytes, InboxWsMessage)
