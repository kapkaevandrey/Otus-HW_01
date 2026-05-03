from http import HTTPStatus
from uuid import UUID

from app.core.enums import ConversationTypes
from app.core.repositories import UnitOfWork
from app.core.services.utils import ServiceUtils
from app.exceptions import BaseServiceError
from app.schemas.dto import ConversationCreateSchema, ConversationDto, ConversationParticipantsCreateSchema
from app.schemas.services import SendMessageServiceSchema


class DialogUtils(ServiceUtils):
    SEND_TO_SELF_ERROR_MESSAGE = "You cant send message to you self"

    def check_message_data(self, data: SendMessageServiceSchema) -> None:
        if data.user_sender == data.user_receiver:
            raise BaseServiceError(status=HTTPStatus.BAD_REQUEST, error_message=self.SEND_TO_SELF_ERROR_MESSAGE)

    async def get_or_create_direct_conversation(
        self,
        sender: UUID,
        receiver: UUID,
        uow: UnitOfWork,
        title: str | None = None,
    ) -> ConversationDto:
        low_id, high_id = (sender, receiver) if sender < receiver else (receiver, sender)
        if not (dto := await uow.conversation_repo.get({"peer_low_id": low_id, "peer_high_id": high_id})):
            dto = await uow.conversation_repo.add(
                ConversationCreateSchema(
                    type=ConversationTypes.DIRECT,
                    created_by=sender,
                    title=title,
                    peer_low_id=low_id,
                    peer_high_id=high_id,
                )
            )
        return dto

    async def add_participants_if_needed(
        self, conversation: ConversationDto, users_ids: set[UUID], uow: UnitOfWork
    ) -> None:
        conv_participants_users = await uow.conversation_participants_repo.get_need_fields(
            ["user_id"], where={"conversation_id": conversation.id}, mapped=False
        )
        if need_add := users_ids - {el[0] for el in conv_participants_users}:  # type: ignore
            data = [
                ConversationParticipantsCreateSchema(conversation_id=conversation.id, user_id=user_id)
                for user_id in need_add
            ]
            await uow.conversation_participants_repo.add_batch(data)
