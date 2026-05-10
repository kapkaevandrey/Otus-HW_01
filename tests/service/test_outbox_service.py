import asyncio
import json
from types import SimpleNamespace

from app.apps.consumers import WsMessagesConsumer
from app.core.enums import EventTypes
from app.core.services import PostService, UserUtils
from app.core.services.tasks import processing_events_outbox_task
from app.schemas.dto import UserFriendCreateSchema
from app.schemas.services import PostCreateServiceSchema


async def test_processing_events_outbox_task_sends_message_to_socket(
    context, websocket_factory, faker, user_one, user_two
):
    ws_topic = "topic.ws.test"
    await context.uow.user_friends_repo.add(
        UserFriendCreateSchema(
            user_id=user_two.id,
            friend_id=user_one.id,
        )
    )
    socket = websocket_factory(1)[0]
    assert await context.socket_manager.connect_user(str(user_two.id), socket)
    post_service = PostService(context)
    create_response = await post_service.create_post(
        user_id=user_one.id,
        data=PostCreateServiceSchema(text=faker.text()),
        user_utils=UserUtils(),
        event_topic="topic.post.events",
    )
    assert create_response.is_success
    assert await context.uow.event_actions_repo.count() == 1

    outbox_task = asyncio.create_task(
        processing_events_outbox_task(
            context=context,
            service_name="test-service",
            topics_map={EventTypes.SEND_NEW_POST_FOR_FRIENDS: ws_topic},
            delay=0.01,
        )
    )
    for _ in range(100):
        if context.kafka_producer.messages[ws_topic]:
            break
        await asyncio.sleep(0.01)
    outbox_task.cancel()
    await asyncio.gather(outbox_task, return_exceptions=True)
    key, value = context.kafka_producer.messages[ws_topic][0]
    assert key == user_two.id.hex.encode()
    assert value["send_to_user_id"] == str(user_two.id)
    assert value["event_type"] == EventTypes.SEND_NEW_POST_FOR_FRIENDS
    assert value["payload"]["postId"] == str(create_response.result.id)
    assert value["payload"]["postText"] == create_response.result.text
    assert value["payload"]["author_user_id"] == str(user_one.id)

    ws_consumer = WsMessagesConsumer(
        consumer_class=object,
        consumer_args=(),
        consumer_kwargs={},
    )
    ws_consumer.__dict__["context"] = context
    await ws_consumer.process_message(
        SimpleNamespace(value=value, timestamp=0),
    )
    ws_message = next(msg for msg in reversed(socket.sent) if msg["type"] == "websocket.send")
    assert ws_message["type"] == "websocket.send"
    payload = json.loads(ws_message["text"])
    assert payload["postId"] == str(create_response.result.id)
    assert payload["postText"] == create_response.result.text
    assert payload["author_user_id"] == str(user_one.id)


async def test_processing_events_outbox_task_concurrent_workers(context, faker, user_one, user_two):
    ws_topic = "topic.ws.concurrent"
    post_service = PostService(context)
    expected_posts_count = 5
    await context.uow.user_friends_repo.add(
        UserFriendCreateSchema(
            user_id=user_two.id,
            friend_id=user_one.id,
        )
    )
    expected_post_ids: set[str] = set()
    initial_messages_count = len(context.kafka_producer.messages[ws_topic])
    for _ in range(expected_posts_count):
        response = await post_service.create_post(
            user_id=user_one.id,
            data=PostCreateServiceSchema(text=faker.text()),
            user_utils=UserUtils(),
            event_topic="topic.post.events",
        )
        assert response.is_success
        expected_post_ids.add(str(response.result.id))

    assert await context.uow.event_actions_repo.count() == expected_posts_count
    tasks = [
        asyncio.create_task(
            processing_events_outbox_task(
                context=context,
                service_name="test-service",
                topics_map={EventTypes.SEND_NEW_POST_FOR_FRIENDS: ws_topic},
                delay=0.01,
            )
        )
        for _ in range(5)
    ]
    outbox_is_empty = False
    for _ in range(200):
        if await context.uow.event_actions_repo.count() == 0:
            outbox_is_empty = True
            break
        await asyncio.sleep(0.01)

    assert outbox_is_empty
    # Let workers reach the idle sleep path so cancellation does not interrupt
    # send-before-delete critical section and cause duplicate deliveries.
    await asyncio.sleep(0.05)

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    sent_messages = list(context.kafka_producer.messages[ws_topic])[initial_messages_count:]
    assert len(sent_messages) == expected_posts_count
    sent_post_ids = {message["payload"]["postId"] for _key, message in sent_messages}
    assert sent_post_ids == expected_post_ids
    assert await context.uow.event_actions_repo.count() == 0
