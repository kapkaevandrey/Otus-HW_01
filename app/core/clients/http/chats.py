from __future__ import annotations

from typing import Any
from uuid import UUID

from app.config import ChatServiceSettings
from app.core.request_context import REQUEST_ID_HEADER
from app.schemas.services.dialogs import DirectMessagesItem, SendMessageServiceResponse

from .base import BaseHttpClient
from .schemas import HttpClientResponse


class ChatServiceClient(BaseHttpClient):
    CLIENT_NAME = "chat_service"

    SEND_MESSAGE_PATH = "/api/v1/dialog/{user_id}/send"
    GET_DIALOG_PATH = "/api/v1/dialog/{user_id}/list"

    @classmethod
    def from_settings(cls, settings: ChatServiceSettings, **kwargs: Any) -> ChatServiceClient:
        return cls(base_url=settings.CHAT_SERVICE_URL, timeout=settings.CHAT_SERVICE_TIMEOUT, **kwargs)

    async def send_message(
        self,
        user_id: UUID,
        text: str,
        *,
        authorization: str,
        request_id: str | None = None,
    ) -> HttpClientResponse:
        return await self.request(
            "POST",
            self.SEND_MESSAGE_PATH.format(user_id=user_id),
            json={"text": text},
            headers=self._build_auth_headers(authorization, request_id),
        )

    async def get_dialog(
        self,
        user_id: UUID,
        *,
        authorization: str,
        request_id: str | None = None,
    ) -> HttpClientResponse:
        return await self.request(
            "GET",
            self.GET_DIALOG_PATH.format(user_id=user_id),
            headers=self._build_auth_headers(authorization, request_id),
        )

    @staticmethod
    def parse_send_message(response: HttpClientResponse) -> SendMessageServiceResponse:
        return SendMessageServiceResponse.model_validate(response.json_data)

    @staticmethod
    def parse_dialog_list(response: HttpClientResponse) -> list[DirectMessagesItem]:
        return [DirectMessagesItem.model_validate(item) for item in response.json_data or []]

    @staticmethod
    def _build_auth_headers(authorization: str, request_id: str | None) -> dict[str, str]:
        headers = {"Authorization": authorization}
        if request_id:
            headers[REQUEST_ID_HEADER] = request_id
        return headers
