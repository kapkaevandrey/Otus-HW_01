from __future__ import annotations

import datetime as dt
from http import HTTPStatus
from uuid import UUID, uuid4

import jwt

from app.config import auth_settings
from app.core.clients.http.schemas import HttpClientRequest, HttpClientResponse
from app.core.enums import ConversationTypes
from app.exceptions import BaseClientError
from app.schemas.services import UserTokenData


class InMemoryChatServiceClient:
    """Test double that emulates chat-service dialog API in process."""

    CLIENT_NAME = "chat_service_test"

    def __init__(self) -> None:
        self._messages: dict[frozenset[UUID], list[dict]] = {}
        self._conversations: dict[frozenset[UUID], UUID] = {}

    async def aclose(self) -> None:
        return None

    async def send_message(
        self,
        user_id: UUID,
        text: str,
        *,
        authorization: str,
        request_id: str | None = None,
    ) -> HttpClientResponse:
        sender_id = self._extract_user_id(authorization)
        if sender_id == user_id:
            raise BaseClientError(
                error_message="You cant send message to you self",
                client_name=self.CLIENT_NAME,
                status=HTTPStatus.BAD_REQUEST,
            )

        pair = self._pair_key(sender_id, user_id)
        conversation_id = self._conversations.setdefault(pair, uuid4())
        message_id = uuid4()
        sent_at = dt.datetime.now(dt.UTC)
        self._messages.setdefault(pair, []).append(
            {
                "from": str(sender_id),
                "to": str(user_id),
                "text": text,
                "sent_at": sent_at.isoformat(),
            }
        )
        return self._success_response(
            method="POST",
            url=f"/api/v1/dialog/{user_id}/send",
            authorization=authorization,
            request_id=request_id,
            payload={"text": text},
            json_data={
                "message_id": str(message_id),
                "conversation_id": str(conversation_id),
                "sender_id": str(sender_id),
                "conversation_type": ConversationTypes.DIRECT,
            },
        )

    async def get_dialog(
        self,
        user_id: UUID,
        *,
        authorization: str,
        request_id: str | None = None,
    ) -> HttpClientResponse:
        sender_id = self._extract_user_id(authorization)
        pair = self._pair_key(sender_id, user_id)
        messages = self._messages.get(pair)
        if not messages:
            return HttpClientResponse(
                request=HttpClientRequest(
                    url=f"/api/v1/dialog/{user_id}/list",
                    method="GET",
                    headers=self._build_headers(authorization, request_id),
                ),
                status=HTTPStatus.NOT_FOUND,
                is_success=False,
                is_json=True,
                json_data={"detail": {"message": "Dialog not exists", "details": {}}},
                headers={"content-type": "application/json"},
            )

        return self._success_response(
            method="GET",
            url=f"/api/v1/dialog/{user_id}/list",
            authorization=authorization,
            request_id=request_id,
            json_data=sorted(messages, key=lambda item: item["sent_at"], reverse=True),
        )

    @staticmethod
    def _extract_user_id(authorization: str) -> UUID:
        token = authorization.split(" ", 1)[1]
        payload = UserTokenData.model_validate(
            jwt.decode(token, auth_settings.JWT_PUB_KEY, algorithms=[auth_settings.JWT_ALG])
        )
        return payload.sub

    @staticmethod
    def _pair_key(first: UUID, second: UUID) -> frozenset[UUID]:
        return frozenset((first, second))

    @staticmethod
    def _build_headers(authorization: str, request_id: str | None) -> dict[str, str]:
        headers = {"Authorization": authorization}
        if request_id:
            from app.core.request_context import REQUEST_ID_HEADER

            headers[REQUEST_ID_HEADER] = request_id
        return headers

    def _success_response(
        self,
        *,
        method: str,
        url: str,
        authorization: str,
        request_id: str | None,
        json_data,
        payload=None,
    ) -> HttpClientResponse:
        return HttpClientResponse(
            request=HttpClientRequest(
                url=url,
                method=method,
                payload=payload,
                headers=self._build_headers(authorization, request_id),
            ),
            status=HTTPStatus.OK,
            is_success=True,
            is_json=True,
            json_data=json_data,
            headers={"content-type": "application/json"},
        )
