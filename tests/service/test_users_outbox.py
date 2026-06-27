import asyncio

from app.core.enums import OutboxAction
from app.core.services import AuthUtils, UserService
from app.core.services.tasks import processing_users_outbox_task
from app.schemas.services import RegisterUserData


async def test_register_user_creates_outbox_event(context, user_one_real_password):
    service = UserService(context)
    response = await service.register_user(
        data=RegisterUserData(
            first_name="John",
            second_name="Doe",
            birthdate="1990-01-01",
            biography="bio",
            city="NYC",
            password=user_one_real_password,
        ),
        auth_utils=AuthUtils(),
    )
    assert response.is_success
    user_id = response.result.user_id

    async with context.uow.transaction(read_only=True) as uow:
        user = await uow.user_repo.get({"id": user_id})
        assert user is not None
        assert user.first_name == "John"

        outbox_items = await uow.users_outbox_repo.get_by_attributes(order_fields=["created_at"])
        assert len(outbox_items) == 1
        assert outbox_items[0].action == OutboxAction.CREATE
        assert outbox_items[0].data["id"] == str(user_id)
        assert outbox_items[0].data["first_name"] == "John"
        assert "password" not in outbox_items[0].data


async def test_processing_users_outbox_publishes_to_kafka(context, user_one_real_password):
    topic = "cud.user.test"
    service = UserService(context)
    register_response = await service.register_user(
        data=RegisterUserData(
            first_name="Jane",
            second_name="Smith",
            birthdate="1991-02-02",
            biography=None,
            city=None,
            password=user_one_real_password,
        ),
        auth_utils=AuthUtils(),
    )
    assert register_response.is_success
    user_id = register_response.result.user_id

    outbox_task = asyncio.create_task(
        processing_users_outbox_task(
            context=context,
            service_name="test-service",
            topic=topic,
            delay=0.01,
        )
    )
    for _ in range(100):
        if context.kafka_producer.messages.get(topic):
            break
        await asyncio.sleep(0.01)
    outbox_task.cancel()
    await asyncio.gather(outbox_task, return_exceptions=True)

    assert context.kafka_producer.messages[topic]
    key, value = context.kafka_producer.messages[topic][0]
    assert key == user_id.hex.encode()
    assert value["action"] == OutboxAction.CREATE
    assert value["data"]["id"] == str(user_id)
    assert value["data"]["first_name"] == "Jane"

    async with context.uow.transaction(read_only=True) as uow:
        assert await uow.users_outbox_repo.count() == 0
