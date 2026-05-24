import datetime as dt
from http import HTTPStatus
from uuid import UUID, uuid4

from app.core.clients import RedisClient
from app.core.enums import ConversationTypes
from app.core.services.utils import ServiceUtils
from app.exceptions import BaseServiceError
from app.schemas.dto import ConversationCreateSchema, ConversationDto, MessageCreateSchema, MessageDto
from app.schemas.services import SendMessageServiceSchema
from app.schemas.services.dialogs import DirectMessagesItem


class DialogUtils(ServiceUtils):
    SEND_TO_SELF_ERROR_MESSAGE = "You cant send message to you self"
    DIALOG_NOT_EXISTS_ERROR_MESSAGE = "Dialog not exists"
    CONVERSATION_MESSAGES = "messages:{conversation_id}"
    PARTICIPANTS_CONVERSATION_REDIS_KEY = "participants:{conversation_id}"
    DIRECT_CONVERSATION_KEY = "direct:conversation:{low_id}:{high_id}"
    MESSAGE_KEY = "message:{message_id}"
    MESSAGE_KEY_PREFIX = "message:"

    def check_message_data(self, data: SendMessageServiceSchema) -> None:
        if data.user_sender == data.user_receiver:
            raise BaseServiceError(status=HTTPStatus.BAD_REQUEST, error_message=self.SEND_TO_SELF_ERROR_MESSAGE)

    async def get_or_create_direct_conversation(
        self,
        sender: UUID,
        receiver: UUID,
        redis_client: RedisClient,
        title: str | None = None,
    ) -> ConversationDto:
        low_id, high_id = (sender, receiver) if sender < receiver else (receiver, sender)
        create_data = ConversationCreateSchema(
            type=ConversationTypes.DIRECT,
            created_by=sender,
            title=title,
            peer_low_id=low_id,
            peer_high_id=high_id,
        )
        dialog_conversation_key = self.DIRECT_CONVERSATION_KEY.format(low_id=low_id, high_id=high_id)
        if conv := await redis_client.get(dialog_conversation_key):
            return ConversationDto.model_validate_json(conv)
        dto = ConversationDto(
            id=uuid4(),
            type=create_data.type,
            created_by=create_data.created_by,
            title=create_data.title,
            peer_low_id=create_data.peer_low_id,
            peer_high_id=create_data.peer_high_id,
            created_at=dt.datetime.now(dt.UTC),
        )
        await redis_client.set(dialog_conversation_key, dto.model_dump_json())
        return dto

    async def get_direct_users_conversation(
        self,
        user_first: UUID,
        user_second: UUID,
        redis_client: RedisClient,
    ) -> ConversationDto:
        low_id, high_id = (user_first, user_second) if user_first < user_second else (user_second, user_first)
        key = self.DIRECT_CONVERSATION_KEY.format(low_id=low_id, high_id=high_id)
        raw = await redis_client.get(key)
        if not raw:
            raise BaseServiceError(status=HTTPStatus.NOT_FOUND, error_message=self.DIALOG_NOT_EXISTS_ERROR_MESSAGE)
        return ConversationDto.model_validate_json(raw)

    async def send_message_to_user_by_script(
        self,
        *,
        sender: UUID,
        receiver: UUID,
        conversation: ConversationDto,
        create_data: MessageCreateSchema,
        redis_client: RedisClient,
    ) -> ConversationDto:
        low_id, high_id = (sender, receiver) if sender < receiver else (receiver, sender)
        direct_conversation_key = self.DIRECT_CONVERSATION_KEY.format(low_id=low_id, high_id=high_id)
        participants_key = self.PARTICIPANTS_CONVERSATION_REDIS_KEY.format(conversation_id=conversation.id)
        messages_key = self.CONVERSATION_MESSAGES.format(conversation_id=conversation.id)
        message_key = self.MESSAGE_KEY.format(message_id=create_data.id)
        raw = await redis_client.send_message_to_user(
            direct_conversation_key=direct_conversation_key,
            participants_key=participants_key,
            messages_key=messages_key,
            message_key=message_key,
            conversation_json_candidate=conversation.model_dump_json(),
            sender_id=str(sender),
            receiver_id=str(receiver),
            message_member=str(create_data.id),
            sent_at_score=create_data.sent_at.timestamp(),
            message_json=create_data.model_dump_json(),
        )
        if len(raw) < 1:
            raise BaseServiceError(status=HTTPStatus.INTERNAL_SERVER_ERROR, error_message="Unexpected script response")
        return ConversationDto.model_validate_json(raw[0])

    async def add_message_to_conversation(
        self,
        create_data: MessageCreateSchema,
        redis_client: RedisClient,
    ) -> None:
        messages_key = self.CONVERSATION_MESSAGES.format(conversation_id=create_data.conversation_id)
        message_key = self.MESSAGE_KEY.format(message_id=create_data.id)
        await redis_client.zadd(messages_key, {str(create_data.id): create_data.sent_at.timestamp()})
        await redis_client.set(message_key, create_data.model_dump_json())

    async def send_message_to_user_procedure(
        self,
        *,
        sender: UUID,
        receiver: UUID,
        text: str,
        redis_client: RedisClient,
    ) -> tuple[ConversationDto, MessageCreateSchema]:
        conversation = await self.get_or_create_direct_conversation(
            sender=sender, receiver=receiver, redis_client=redis_client
        )
        create_data = MessageCreateSchema(sender_id=sender, conversation_id=conversation.id, text=text)
        conversation = await self.send_message_to_user_by_script(
            sender=sender,
            receiver=receiver,
            conversation=conversation,
            create_data=create_data,
            redis_client=redis_client,
        )
        return conversation, create_data

    async def get_dialog_with_users_procedure(
        self,
        *,
        user_first: UUID,
        user_second: UUID,
        redis_client: RedisClient,
    ) -> list[DirectMessagesItem]:
        conversation = await self.get_direct_users_conversation(
            user_first=user_first,
            user_second=user_second,
            redis_client=redis_client,
        )
        messages_key = self.CONVERSATION_MESSAGES.format(conversation_id=conversation.id)
        raw_messages = await redis_client.get_dialog_with_users(
            messages_key=messages_key,
            message_key_prefix=self.MESSAGE_KEY_PREFIX,
            offset=0,
            limit=1000,
            order="desc",
        )
        result: list[DirectMessagesItem] = []
        for raw in raw_messages:
            msg = MessageDto.model_validate_json(raw)
            result.append(
                DirectMessagesItem(
                    text=msg.text,
                    sent_at=msg.sent_at,
                    from_user=msg.sender_id,
                    to_user=user_first if user_second == msg.sender_id else user_second,
                )
            )
        return result
