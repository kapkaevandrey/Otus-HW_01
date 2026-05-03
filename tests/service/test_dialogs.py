from uuid import uuid4

from app.core.enums import ConversationTypes
from app.core.services import DialogService, UserUtils
from app.schemas.dto import ConversationCreateSchema, ConversationParticipantsCreateSchema
from app.schemas.services import SendMessageServiceResponse, SendMessageServiceSchema


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
