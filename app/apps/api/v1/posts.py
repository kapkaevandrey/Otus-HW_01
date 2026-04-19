from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, Header

from app.apps.api.utils import raise_http_exception_from_service_response
from app.config import auth_settings
from app.core.containers import Context, get_context
from app.core.services import AuthUtils, PostService, UserUtils
from app.schemas.services import (
    AuthTokenInfo,
    GetPostServiceResponseSchema,
    PostCreateServiceSchema,
    PostUpdateServiceSchema,
)


users_router = APIRouter(prefix="/post")


@users_router.post(
    "/create",
    status_code=HTTPStatus.OK,
)
async def add_new_post(
    data: PostCreateServiceSchema,
    auth_header: str = Header("", alias=auth_settings.AUTH_HEADER_KEY),
    context: Context = Depends(get_context),
) -> GetPostServiceResponseSchema:
    service = PostService(context=context)
    service_response = await service.create_post(
        data=data,
        auth_info=AuthTokenInfo(
            alg=auth_settings.JWT_ALG, public_key=auth_settings.JWT_PUB_KEY, token_type=auth_settings.AUTH_TOKEN_TYPE
        ),
        auth_header=auth_header,
        auth_utils=AuthUtils(),
        user_utils=UserUtils(),
    )
    raise_http_exception_from_service_response(service_response)
    return service_response.result


@users_router.put(
    "/update",
    status_code=HTTPStatus.OK,
)
async def update_post(
    data: PostUpdateServiceSchema,
    auth_header: str = Header("", alias=auth_settings.AUTH_HEADER_KEY),
    context: Context = Depends(get_context),
) -> GetPostServiceResponseSchema:
    service = PostService(context=context)
    service_response = await service.update_post(
        data=data,
        auth_info=AuthTokenInfo(
            alg=auth_settings.JWT_ALG, public_key=auth_settings.JWT_PUB_KEY, token_type=auth_settings.AUTH_TOKEN_TYPE
        ),
        auth_header=auth_header,
        auth_utils=AuthUtils(),
    )
    raise_http_exception_from_service_response(service_response)
    return service_response.result


@users_router.delete(
    "/delete/{post_id}",
    status_code=HTTPStatus.NO_CONTENT,
)
async def remove_post(
    post_id: UUID,
    auth_header: str = Header("", alias=auth_settings.AUTH_HEADER_KEY),
    context: Context = Depends(get_context),
) -> None:
    service = PostService(context=context)
    service_response = await service.remove_post(
        post_id=post_id,
        auth_info=AuthTokenInfo(
            alg=auth_settings.JWT_ALG, public_key=auth_settings.JWT_PUB_KEY, token_type=auth_settings.AUTH_TOKEN_TYPE
        ),
        auth_header=auth_header,
        auth_utils=AuthUtils(),
    )
    raise_http_exception_from_service_response(service_response)
    return None


@users_router.get(
    "/get/{post_id}",
    status_code=HTTPStatus.OK,
)
async def get_post(
    post_id: UUID,
    context: Context = Depends(get_context),
) -> GetPostServiceResponseSchema:
    service = PostService(context=context)
    service_response = await service.get_post(post_id=post_id)
    raise_http_exception_from_service_response(service_response)
    return service_response.result


@users_router.get(
    "/feed",
    status_code=HTTPStatus.OK,
)
async def get_last_friends_posts(
    auth_header: str = Header("", alias=auth_settings.AUTH_HEADER_KEY),
    context: Context = Depends(get_context),
) -> list[GetPostServiceResponseSchema]:
    service = PostService(context=context)
    service_response = await service.get_friends_last_posts(
        auth_header=auth_header,
        auth_info=AuthTokenInfo(
            alg=auth_settings.JWT_ALG, public_key=auth_settings.JWT_PUB_KEY, token_type=auth_settings.AUTH_TOKEN_TYPE
        ),
        auth_utils=AuthUtils(),
        user_utils=UserUtils(),
    )
    raise_http_exception_from_service_response(service_response)
    return service_response.result
