from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends

from app.apps.api.auth import get_user_data_access
from app.apps.api.utils import raise_http_exception_from_service_response
from app.config import kafka_settings
from app.core.containers import Context, get_context
from app.core.services import UserService
from app.schemas.services import UserTokenData


friends_router = APIRouter(prefix="/friend", tags=["Friends"])


@friends_router.put(
    "/set/{user_id}",
    status_code=HTTPStatus.OK,
)
async def add_to_friends(
    user_id: UUID,
    user_data: UserTokenData = Depends(get_user_data_access),
    context: Context = Depends(get_context),
) -> None:
    service = UserService(context)
    service_response = await service.add_to_friends(
        user_id=user_data.sub,
        friend_id=user_id,
        event_topic=kafka_settings.SERVICE_USER_EVENT_TOPIC,
    )
    raise_http_exception_from_service_response(service_response)
    return service_response.result


@friends_router.delete(
    "/delete/{user_id}",
    status_code=HTTPStatus.OK,
)
async def remove_from_friends(
    user_id: UUID,
    user_data: UserTokenData = Depends(get_user_data_access),
    context: Context = Depends(get_context),
) -> None:
    service = UserService(context)
    service_response = await service.remove_from_friends(
        user_id=user_data.sub,
        friend_id=user_id,
        event_topic=kafka_settings.SERVICE_USER_EVENT_TOPIC,
    )
    raise_http_exception_from_service_response(service_response)
    return None
