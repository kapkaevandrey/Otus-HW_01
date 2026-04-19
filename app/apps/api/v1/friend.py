from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, Header

from app.apps.api.utils import raise_http_exception_from_service_response
from app.config import auth_settings
from app.core.containers import Context, get_context
from app.core.services import AuthUtils, UserService
from app.schemas.services import AuthTokenInfo


users_router = APIRouter(prefix="/friend")


@users_router.put(
    "/set/{user_id}",
    status_code=HTTPStatus.OK,
)
async def add_to_friends(
    user_id: UUID,
    auth_header: str = Header("", alias=auth_settings.AUTH_HEADER_KEY),
    context: Context = Depends(get_context),
) -> None:
    service = UserService(context)
    service_response = await service.add_to_friends(
        friend_id=user_id,
        auth_header=auth_header,
        token_info=AuthTokenInfo(
            alg=auth_settings.JWT_ALG, public_key=auth_settings.JWT_PUB_KEY, token_type=auth_settings.AUTH_TOKEN_TYPE
        ),
        auth_utils=AuthUtils(),
    )
    raise_http_exception_from_service_response(service_response)
    return service_response.result


@users_router.delete(
    "/delete/{user_id}",
    status_code=HTTPStatus.OK,
)
async def remove_from_friends(
    user_id: UUID,
    auth_header: str = Header("", alias=auth_settings.AUTH_HEADER_KEY),
    context: Context = Depends(get_context),
) -> None:
    service = UserService(context)
    service_response = await service.remove_from_friends(
        friend_id=user_id,
        auth_header=auth_header,
        token_info=AuthTokenInfo(
            alg=auth_settings.JWT_ALG, public_key=auth_settings.JWT_PUB_KEY, token_type=auth_settings.AUTH_TOKEN_TYPE
        ),
        auth_utils=AuthUtils(),
    )
    raise_http_exception_from_service_response(service_response)
    return None
