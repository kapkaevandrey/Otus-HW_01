from uuid import uuid4

import jwt

from app.config import auth_settings
from app.core.enums import ConversationTypes, ScopeType
from app.core.services import DialogService, UserUtils
from app.schemas.services import SendMessageServiceSchema, UserTokenData


def make_authorization(user_id) -> str:
    payload = UserTokenData(sub=user_id, scope=ScopeType.ACCESS).model_dump(mode="json")
    token = jwt.encode(payload=payload, key=auth_settings.JWT_PRIVATE_KEY, algorithm=auth_settings.JWT_ALG)
    return f"{auth_settings.AUTH_TOKEN_TYPE} {token}"


async def test_send_message_to_self(user_one, context):
    data = SendMessageServiceSchema(
        text=uuid4().hex,
        user_sender=user_one.id,
        user_receiver=user_one.id,
    )
    service = DialogService(context)
    service_response = await service.send_message_to_user(
        data=data,
        user_utils=UserUtils(),
        authorization=make_authorization(user_one.id),
        request_id="req-1",
    )
    assert service_response.is_success is False


async def test_send_message_to_user_proxies_chat_service(user_one, user_two, context):
    data = SendMessageServiceSchema(
        text=uuid4().hex,
        user_sender=user_one.id,
        user_receiver=user_two.id,
    )
    service = DialogService(context)
    service_response = await service.send_message_to_user(
        data=data,
        user_utils=UserUtils(),
        authorization=make_authorization(user_one.id),
        request_id="req-2",
    )
    assert service_response.is_success
    assert service_response.result.sender_id == user_one.id
    assert service_response.result.conversation_type == ConversationTypes.DIRECT


async def test_get_users_dialogs_conversation_not_found(user_one, user_two, context):
    service = DialogService(context)
    service_response = await service.get_dialog_with_users(
        user_first=user_one.id,
        user_second=user_two.id,
        authorization=make_authorization(user_one.id),
        request_id="req-3",
    )
    assert service_response.is_success is False


async def test_get_users_dialog(user_one, user_two, context):
    service = DialogService(context)
    send_data = SendMessageServiceSchema(
        text="hello",
        user_sender=user_one.id,
        user_receiver=user_two.id,
    )
    await service.send_message_to_user(
        data=send_data,
        user_utils=UserUtils(),
        authorization=make_authorization(user_one.id),
        request_id="req-4",
    )
    service_response = await service.get_dialog_with_users(
        user_first=user_one.id,
        user_second=user_two.id,
        authorization=make_authorization(user_one.id),
        request_id="req-5",
    )
    assert service_response.is_success is True
    assert len(service_response.result) == 1
    assert service_response.result[0].text == "hello"


async def test_get_users_dialog_sorted(user_one, user_two, context):
    service = DialogService(context)
    for index in range(3):
        await service.send_message_to_user(
            data=SendMessageServiceSchema(
                text=f"message-{index}",
                user_sender=user_one.id,
                user_receiver=user_two.id,
            ),
            user_utils=UserUtils(),
            authorization=make_authorization(user_one.id),
            request_id=f"req-send-{index}",
        )

    service_response = await service.get_dialog_with_users(
        user_first=user_one.id,
        user_second=user_two.id,
        authorization=make_authorization(user_one.id),
        request_id="req-list",
    )
    assert service_response.is_success
    assert len(service_response.result) == 3
    assert service_response.result == sorted(service_response.result, key=lambda item: item.sent_at, reverse=True)
