from http import HTTPStatus
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.apps.api.auth import get_user_data_access
from app.apps.utils import raise_http_exception_from_service_response
from app.config import auth_settings
from app.core.containers import Context, get_context
from app.core.request_context import get_request_id
from app.core.services import DialogService, UserUtils
from app.schemas.api import SendMessageSchema
from app.schemas.services import BaseServiceResponse, SendMessageServiceSchema, UserTokenData
from app.schemas.services.dialogs import DirectMessagesItem, SendMessageServiceResponse


dialog_router = APIRouter(prefix="/dialog", tags=["Dialogs"])


def _dialog_proxy_response(service_response: BaseServiceResponse[Any]) -> JSONResponse:
    raise_http_exception_from_service_response(service_response)
    return JSONResponse(status_code=service_response.status, content=service_response.result)


@dialog_router.post(
    "/{user_id}/send",
    status_code=HTTPStatus.OK,
    response_model=SendMessageServiceResponse,
)
async def send_message_to_user(
    user_id: UUID,
    data: SendMessageSchema,
    request: Request,
    user_data: UserTokenData = Depends(get_user_data_access),
    context: Context = Depends(get_context),
) -> JSONResponse:
    service = DialogService(context)
    service_response = await service.send_message_to_user(
        data=SendMessageServiceSchema(text=data.text, user_sender=user_data.sub, user_receiver=user_id),
        user_utils=UserUtils(),
        authorization=request.headers[auth_settings.AUTH_HEADER_KEY],
        request_id=get_request_id(),
    )
    return _dialog_proxy_response(service_response)


@dialog_router.get(
    "/{user_id}/list",
    status_code=HTTPStatus.OK,
    response_model=list[DirectMessagesItem],
)
async def get_users_dialog(
    user_id: UUID,
    request: Request,
    user_data: UserTokenData = Depends(get_user_data_access),
    context: Context = Depends(get_context),
) -> JSONResponse:
    service = DialogService(context)
    service_response = await service.get_dialog_with_users(
        user_first=user_data.sub,
        user_second=user_id,
        authorization=request.headers[auth_settings.AUTH_HEADER_KEY],
        request_id=get_request_id(),
    )
    return _dialog_proxy_response(service_response)
