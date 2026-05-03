from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends

from app.apps.api.auth import get_user_data_access
from app.apps.api.utils import raise_http_exception_from_service_response
from app.core.containers import Context, get_context
from app.core.services import DialogService, UserUtils
from app.schemas.api import SendMessageSchema
from app.schemas.services import SendMessageServiceResponse, SendMessageServiceSchema, UserTokenData
from app.schemas.services.dialogs import DirectMessagesItem


dialog_router = APIRouter(prefix="/dialog", tags=["Dialogs"])


@dialog_router.post(
    "/{user_id}/send",
    status_code=HTTPStatus.OK,
)
async def send_message_to_user(
    user_id: UUID,
    data: SendMessageSchema,
    user_data: UserTokenData = Depends(get_user_data_access),
    context: Context = Depends(get_context),
) -> SendMessageServiceResponse:
    service = DialogService(context)
    service_response = await service.send_message_to_user(
        data=SendMessageServiceSchema(text=data.text, user_sender=user_data.sub, user_receiver=user_id),
        user_utils=UserUtils(),
    )
    raise_http_exception_from_service_response(service_response)
    return service_response.result


@dialog_router.get(
    "/{user_id}/list",
    status_code=HTTPStatus.OK,
)
async def get_users_dialog(
    user_id: UUID,
    user_data: UserTokenData = Depends(get_user_data_access),
    context: Context = Depends(get_context),
) -> list[DirectMessagesItem]:
    service = DialogService(context)
    service_response = await service.get_dialog_with_users(
        user_first=user_data.sub,
        user_second=user_id,
    )
    raise_http_exception_from_service_response(service_response)
    return service_response.result
