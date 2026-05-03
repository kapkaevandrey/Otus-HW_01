from functools import cached_property
from uuid import UUID

from app.core.services.base import BaseService, async_use_case
from app.core.services.user import UserUtils
from app.schemas.dto import MessageCreateSchema
from app.schemas.services import BaseServiceResponse, SendMessageServiceResponse, SendMessageServiceSchema
from app.schemas.services.dialogs import DirectMessagesItem

from .utils import DialogUtils


class DialogService(BaseService):
    @cached_property
    def utils(self) -> DialogUtils:
        return DialogUtils()

    @async_use_case()
    async def send_message_to_user(
        self, *, data: SendMessageServiceSchema, user_utils: UserUtils
    ) -> BaseServiceResponse[SendMessageServiceResponse]:
        response = BaseServiceResponse[SendMessageServiceResponse]()
        self.utils.check_message_data(data)
        async with self.context.uow.transaction() as uow:
            sender = await user_utils.get_user_by_id(data.user_sender, uow)
            await user_utils.get_user_by_id(data.user_receiver, uow)
            conversation = await self.utils.get_or_create_direct_conversation(
                sender=data.user_sender, receiver=data.user_receiver, uow=uow
            )
            await self.utils.add_participants_if_needed(conversation, {data.user_sender, data.user_receiver}, uow)
            message = await uow.message_repo.add(
                MessageCreateSchema(sender_id=sender.id, conversation_id=conversation.id, text=data.text)
            )
            response.result = SendMessageServiceResponse(
                message_id=message.id,
                sender_id=sender.id,
                conversation_id=conversation.id,
                conversation_type=conversation.type,
            )
        return response

    @async_use_case()
    async def get_dialog_with_users(
        self, *, user_first: UUID, user_second: UUID
    ) -> BaseServiceResponse[list[DirectMessagesItem]]:
        response = BaseServiceResponse[list[DirectMessagesItem]]()
        async with self.context.uow.transaction() as uow:
            conv = await self.utils.get_direct_users_conversation(user_first, user_second, uow)
            messages = await uow.message_repo.get_by_attributes(
                {"conversation_id": conv.id}, order_fields=["sent_at__desc"]
            )
            response.result = [
                DirectMessagesItem(
                    text=el.text,
                    sent_at=el.sent_at,
                    from_user=el.sender_id,
                    to_user=user_first if user_second == el.sender_id else user_second,
                )
                for el in messages
            ]
        return response
