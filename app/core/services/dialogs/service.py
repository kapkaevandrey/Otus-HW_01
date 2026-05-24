from functools import cached_property
from uuid import UUID

from app.core.services.base import BaseService, async_use_case
from app.core.services.user import UserUtils
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
        conversation, create_data = await self.utils.send_message_to_user_procedure(
            sender=data.user_sender,
            receiver=data.user_receiver,
            text=data.text,
            redis_client=self.context.redis_client,
        )
        response.result = SendMessageServiceResponse(
            message_id=create_data.id,
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
        response.result = await self.utils.get_dialog_with_users_procedure(
            user_first=user_first,
            user_second=user_second,
            redis_client=self.context.redis_client,
        )
        return response
