from functools import cached_property
from typing import Any
from uuid import UUID

from app.core.clients.http.base import BaseHttpClient
from app.core.clients.http.schemas import HttpClientResponse
from app.core.services.base import BaseService, async_use_case
from app.core.services.user import UserUtils
from app.exceptions import BaseClientError, BaseServiceError
from app.schemas.services import BaseServiceResponse, SendMessageServiceSchema

from .utils import DialogUtils


class DialogService(BaseService):
    @cached_property
    def utils(self) -> DialogUtils:
        return DialogUtils()

    @staticmethod
    def _apply_success_http_response(
        response: BaseServiceResponse[Any],
        http_response: HttpClientResponse,
    ) -> BaseServiceResponse[Any]:
        if not http_response.is_success:
            error_message, error_details = BaseHttpClient._extract_error_payload(http_response)
            raise BaseServiceError(
                error_message=error_message,
                status=http_response.status,
                error_details=error_details,
            )
        response.status = http_response.status
        response.result = http_response.json_data if http_response.is_json else http_response.text
        return response

    @async_use_case()
    async def send_message_to_user(
        self,
        *,
        data: SendMessageServiceSchema,
        user_utils: UserUtils,
        authorization: str,
        request_id: str | None = None,
    ) -> BaseServiceResponse[Any]:
        response = BaseServiceResponse[Any]()
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

        return self._apply_success_http_response(response, http_response)

    @async_use_case()
    async def get_dialog_with_users(
        self,
        *,
        user_first: UUID,
        user_second: UUID,
        authorization: str,
        request_id: str | None = None,
    ) -> BaseServiceResponse[Any]:
        response = BaseServiceResponse[Any]()
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

        return self._apply_success_http_response(response, http_response)
