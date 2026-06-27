from functools import cached_property
from uuid import UUID

from app.core.services.base import BaseService, async_use_case
from app.core.services.user import UserUtils
from app.exceptions import BaseClientError, BaseServiceError
from app.schemas.services import BaseServiceResponse, SendMessageServiceResponse, SendMessageServiceSchema
from app.schemas.services.dialogs import DirectMessagesItem

from .utils import DialogUtils


class DialogService(BaseService):
    @cached_property
    def utils(self) -> DialogUtils:
        return DialogUtils()

    @async_use_case()
    async def send_message_to_user(
        self,
        *,
        data: SendMessageServiceSchema,
        user_utils: UserUtils,
        authorization: str,
        request_id: str | None = None,
    ) -> BaseServiceResponse[SendMessageServiceResponse]:
        response = BaseServiceResponse[SendMessageServiceResponse]()
        self.utils.check_message_data(data)
        async with self.context.uow.transaction() as uow:
            await user_utils.get_user_by_id(data.user_sender, uow)
            await user_utils.get_user_by_id(data.user_receiver, uow)

        try:
            http_response = await self.context.chat_service_client.send_message(
                user_id=data.user_receiver,
                text=data.text,
                authorization=authorization,
                request_id=request_id,
            )
        except BaseClientError as exc:
            raise BaseServiceError(
                error_message=exc.error_message,
                status=exc.status,
                error_details=exc.error_details,
            ) from exc

        response.result = self.context.chat_service_client.parse_send_message(http_response)
        return response

    @async_use_case()
    async def get_dialog_with_users(
        self,
        *,
        user_first: UUID,
        user_second: UUID,
        authorization: str,
        request_id: str | None = None,
    ) -> BaseServiceResponse[list[DirectMessagesItem]]:
        response = BaseServiceResponse[list[DirectMessagesItem]]()
        try:
            http_response = await self.context.chat_service_client.get_dialog(
                user_id=user_second,
                authorization=authorization,
                request_id=request_id,
            )
        except BaseClientError as exc:
            raise BaseServiceError(
                error_message=exc.error_message,
                status=exc.status,
                error_details=exc.error_details,
            ) from exc

        response.result = self.context.chat_service_client.parse_dialog_list(http_response)
        return response
