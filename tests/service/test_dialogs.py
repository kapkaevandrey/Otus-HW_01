import random as rnd
from uuid import uuid4

from app.core.enums import ConversationTypes
from app.core.services import DialogService, UserUtils
from app.schemas.dto import ConversationCreateSchema, ConversationParticipantsCreateSchema, MessageCreateSchema
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
    uow = context.uow
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
    conversations = await uow.conversation_repo.get_by_attributes()
    assert len(conversations) == 1
    conversation = conversations[0]
    assert conversation.type == ConversationTypes.DIRECT
    assert conversation.peer_low_id == low_id
    assert conversation.peer_high_id == high_id
    assert conversation.created_by == user_one.id
    conv_participants = await uow.conversation_participants_repo.get_by_attributes()
    participants_ids = {el.user_id for el in conv_participants}
    assert len(conv_participants) == 2
    assert participants_ids == {user_one.id, user_two.id}
    for conv_participant in conv_participants:
        assert conv_participant.conversation_id == conversation.id
    messages = await uow.message_repo.get_by_attributes()
    assert len(messages) == 1
    message = messages[0]
    assert message.conversation_id == conversation.id
    assert message.sender_id == user_one.id
    assert message.text == data.text
    assert result == SendMessageServiceResponse(
        conversation_id=conversation.id,
        message_id=message.id,
        conversation_type=conversation.type,
        sender_id=user_one.id,
    )


async def test_send_message_to_user_conversation_exists(
    user_one,
    user_two,
    context,
):
    uow = context.uow
    high_id, low_id = (user_one.id, user_two.id) if user_one.id > user_two.id else (user_two.id, user_one.id)
    conversation = await uow.conversation_repo.add(
        ConversationCreateSchema(
            type=ConversationTypes.DIRECT, created_by=user_one.id, peer_low_id=low_id, peer_high_id=high_id
        ),
    )
    data = SendMessageServiceSchema(
        text=uuid4().hex,
        user_sender=user_one.id,
        user_receiver=user_two.id,
    )
    service = DialogService(context)
    service_response = await service.send_message_to_user(data=data, user_utils=UserUtils())
    assert service_response.is_success
    result = service_response.result
    conv_participants = await uow.conversation_participants_repo.get_by_attributes({"conversation_id": conversation.id})
    participants_ids = {el.user_id for el in conv_participants}
    assert len(conv_participants) == 2
    assert participants_ids == {user_one.id, user_two.id}
    for conv_participant in conv_participants:
        assert conv_participant.conversation_id == conversation.id
    messages = await uow.message_repo.get_by_attributes()
    assert len(messages) == 1
    message = messages[0]
    assert message.conversation_id == conversation.id
    assert message.sender_id == user_one.id
    assert message.text == data.text
    assert result == SendMessageServiceResponse(
        conversation_id=conversation.id,
        message_id=message.id,
        conversation_type=conversation.type,
        sender_id=user_one.id,
    )


async def test_send_message_to_user_conversation_exists_one_participant_exist(
    user_one,
    user_two,
    context,
):
    uow = context.uow
    high_id, low_id = (user_one.id, user_two.id) if user_one.id > user_two.id else (user_two.id, user_one.id)
    conversation = await uow.conversation_repo.add(
        ConversationCreateSchema(
            type=ConversationTypes.DIRECT, created_by=user_one.id, peer_low_id=low_id, peer_high_id=high_id
        ),
    )
    await uow.conversation_participants_repo.add(
        ConversationParticipantsCreateSchema(conversation_id=conversation.id, user_id=user_one.id)
    )
    data = SendMessageServiceSchema(
        text=uuid4().hex,
        user_sender=user_one.id,
        user_receiver=user_two.id,
    )
    service = DialogService(context)
    service_response = await service.send_message_to_user(data=data, user_utils=UserUtils())
    assert service_response.is_success
    result = service_response.result
    conv_participants = await uow.conversation_participants_repo.get_by_attributes({"conversation_id": conversation.id})
    participants_ids = {el.user_id for el in conv_participants}
    assert len(conv_participants) == 2
    assert participants_ids == {user_one.id, user_two.id}
    for conv_participant in conv_participants:
        assert conv_participant.conversation_id == conversation.id
    messages = await uow.message_repo.get_by_attributes()
    assert len(messages) == 1
    message = messages[0]
    assert message.conversation_id == conversation.id
    assert message.sender_id == user_one.id
    assert message.text == data.text
    assert result == SendMessageServiceResponse(
        conversation_id=conversation.id,
        message_id=message.id,
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
    uow = context.uow
    high_id, low_id = (user_one.id, user_two.id) if user_one.id > user_two.id else (user_two.id, user_one.id)
    conversation = await uow.conversation_repo.add(
        ConversationCreateSchema(
            type=ConversationTypes.DIRECT, created_by=user_one.id, peer_low_id=low_id, peer_high_id=high_id
        ),
    )
    messages = await uow.message_repo.add_batch(
        [
            MessageCreateSchema(sender_id=rnd.choice(users_ids), conversation_id=conversation.id, text=uuid4().hex)
            for _ in range(items)
        ]
    )
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
