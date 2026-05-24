import datetime as dt
import random as rnd
from uuid import uuid4

from app.core.enums import ConversationTypes
from app.core.services import DialogService, DialogUtils, UserUtils
from app.schemas.dto import ConversationCreateSchema, ConversationDto, MessageCreateSchema
from app.schemas.services import SendMessageServiceResponse, SendMessageServiceSchema
from app.schemas.services.dialogs import DirectMessagesItem


async def test_send_message_to_self(
    user_one,
    user_two,
    context,
):
    data = SendMessageServiceSchema(
        text=uuid4().hex,
        user_sender=user_one.id,
        user_receiver=user_one.id,
    )
    service = DialogService(context)
    service_response = await service.send_message_to_user(data=data, user_utils=UserUtils())
    assert service_response.is_success is False


async def test_send_message_to_user_new_conversation(
    user_one,
    user_two,
    context,
):
    utils = DialogUtils()
    redis = context.redis_client
    high_id, low_id = (user_one.id, user_two.id) if user_one.id > user_two.id else (user_two.id, user_one.id)
    data = SendMessageServiceSchema(
        text=uuid4().hex,
        user_sender=user_one.id,
        user_receiver=user_two.id,
    )
    service = DialogService(context)
    service_response = await service.send_message_to_user(data=data, user_utils=UserUtils())
    assert service_response.is_success
    result = service_response.result

    direct_key = utils.DIRECT_CONVERSATION_KEY.format(low_id=low_id, high_id=high_id)
    raw_conversation = await redis.get(direct_key)
    assert raw_conversation is not None
    conv_dto = ConversationDto.model_validate_json(raw_conversation)

    participants_key = utils.PARTICIPANTS_CONVERSATION_REDIS_KEY.format(conversation_id=conv_dto.id)
    participants = await redis.smembers(participants_key)
    participants_ids = {el.decode("utf-8") if isinstance(el, bytes) else str(el) for el in participants}
    assert participants_ids == {str(user_one.id), str(user_two.id)}

    messages_key = utils.CONVERSATION_MESSAGES.format(conversation_id=conv_dto.id)
    message_ids = await redis.zrange(messages_key, 0, -1)
    assert len(message_ids) == 1
    message_id = message_ids[0].decode("utf-8") if isinstance(message_ids[0], bytes) else str(message_ids[0])
    raw_message = await redis.get(utils.MESSAGE_KEY.format(message_id=message_id))
    msg_dto = MessageCreateSchema.model_validate_json(raw_message)
    assert msg_dto.conversation_id == conv_dto.id
    assert msg_dto.sender_id == user_one.id
    assert msg_dto.text == data.text

    assert result == SendMessageServiceResponse(
        conversation_id=conv_dto.id,
        message_id=msg_dto.id,
        conversation_type=conv_dto.type,
        sender_id=user_one.id,
    )


async def test_send_message_to_user_conversation_exists(
    user_one,
    user_two,
    context,
):
    utils = DialogUtils()
    redis = context.redis_client
    data = SendMessageServiceSchema(
        text=uuid4().hex,
        user_sender=user_one.id,
        user_receiver=user_two.id,
    )
    service = DialogService(context)
    first = await service.send_message_to_user(data=data, user_utils=UserUtils())
    second = await service.send_message_to_user(data=data, user_utils=UserUtils())
    assert first.is_success and second.is_success
    assert first.result.conversation_id == second.result.conversation_id

    messages_key = utils.CONVERSATION_MESSAGES.format(conversation_id=first.result.conversation_id)
    assert await redis.zcard(messages_key) == 2


async def test_send_message_to_user_conversation_exists_one_participant_exist(
    user_one,
    user_two,
    context,
):
    utils = DialogUtils()
    redis = context.redis_client
    high_id, low_id = (user_one.id, user_two.id) if user_one.id > user_two.id else (user_two.id, user_one.id)
    existing_conv = ConversationCreateSchema(
        type=ConversationTypes.DIRECT, created_by=user_one.id, peer_low_id=low_id, peer_high_id=high_id
    )
    direct_key = utils.DIRECT_CONVERSATION_KEY.format(low_id=low_id, high_id=high_id)
    conversation = ConversationDto(
        id=uuid4(),
        type=existing_conv.type,
        created_by=existing_conv.created_by,
        title=existing_conv.title,
        peer_low_id=existing_conv.peer_low_id,
        peer_high_id=existing_conv.peer_high_id,
        created_at=dt.datetime.now(dt.UTC),
    )
    await redis.set(direct_key, conversation.model_dump_json())
    participants_key = utils.PARTICIPANTS_CONVERSATION_REDIS_KEY.format(conversation_id=conversation.id)
    await redis.sadd(participants_key, str(user_one.id))

    data = SendMessageServiceSchema(
        text=uuid4().hex,
        user_sender=user_one.id,
        user_receiver=user_two.id,
    )
    service = DialogService(context)
    service_response = await service.send_message_to_user(data=data, user_utils=UserUtils())
    assert service_response.is_success
    participants = await redis.smembers(participants_key)
    participants_ids = {el.decode("utf-8") if isinstance(el, bytes) else str(el) for el in participants}
    assert participants_ids == {str(user_one.id), str(user_two.id)}
    assert service_response.result == SendMessageServiceResponse(
        conversation_id=conversation.id,
        message_id=service_response.result.message_id,
        conversation_type=conversation.type,
        sender_id=user_one.id,
    )


async def test_get_users_dialogs_conversation_not_found(
    user_one,
    user_two,
    context,
):
    service = DialogService(context)
    service_response = await service.get_dialog_with_users(
        user_first=user_one.id,
        user_second=user_two.id,
    )
    assert service_response.is_success is False


async def test_get_users_dialog(
    user_one,
    user_two,
    context,
):
    items = 500
    users_ids = [user_one.id, user_two.id]
    utils = DialogUtils()
    redis = context.redis_client
    conversation = await utils.get_or_create_direct_conversation(
        sender=user_one.id, receiver=user_two.id, redis_client=redis
    )
    messages = []
    for _ in range(items):
        message = MessageCreateSchema(
            sender_id=rnd.choice(users_ids),
            conversation_id=conversation.id,
            text=uuid4().hex,
        )
        messages.append(message)
        await utils.add_message_to_conversation(message, redis)

    expected = [
        DirectMessagesItem(
            text=el.text,
            from_user=el.sender_id,
            to_user=user_one.id if el.sender_id == user_two.id else user_two.id,
            sent_at=el.sent_at,
        )
        for el in messages
    ]
    expected.sort(key=lambda el: el.sent_at, reverse=True)
    service = DialogService(context)
    service_response = await service.get_dialog_with_users(
        user_first=user_one.id,
        user_second=user_two.id,
    )
    assert service_response.is_success is True
    assert service_response.result == expected
