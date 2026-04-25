from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends

from app.apps.api.auth import get_user_data_access
from app.apps.api.utils import raise_http_exception_from_service_response
from app.config import kafka_settings
from app.core.containers import Context, get_context
from app.core.services import PostService, UserUtils
from app.schemas.services import (
    GetPostServiceResponseSchema,
    PostCreateServiceSchema,
    PostUpdateServiceSchema,
    UserTokenData,
)


posts_router = APIRouter(prefix="/post", tags=["Post"])


@posts_router.post(
    "/create",
    status_code=HTTPStatus.OK,
)
async def add_new_post(
    data: PostCreateServiceSchema,
    user_data: UserTokenData = Depends(get_user_data_access),
    context: Context = Depends(get_context),
) -> GetPostServiceResponseSchema:
    service = PostService(context=context)
    service_response = await service.create_post(
        user_id=user_data.sub,
        data=data,
        user_utils=UserUtils(),
        event_topic=kafka_settings.SERVICE_USER_PUBLICATION_TOPIC,
    )
    raise_http_exception_from_service_response(service_response)
    return service_response.result


@posts_router.put(
    "/update",
    status_code=HTTPStatus.OK,
)
async def update_post(
    data: PostUpdateServiceSchema,
    user_data: UserTokenData = Depends(get_user_data_access),
    context: Context = Depends(get_context),
) -> GetPostServiceResponseSchema:
    service = PostService(context=context)
    service_response = await service.update_post(
        user_id=user_data.sub,
        data=data,
        event_topic=kafka_settings.SERVICE_USER_PUBLICATION_TOPIC,
    )
    raise_http_exception_from_service_response(service_response)
    return service_response.result


@posts_router.delete(
    "/delete/{post_id}",
    status_code=HTTPStatus.NO_CONTENT,
)
async def remove_post(
    post_id: UUID,
    user_data: UserTokenData = Depends(get_user_data_access),
    context: Context = Depends(get_context),
) -> None:
    service = PostService(context=context)
    service_response = await service.remove_post(
        post_id=post_id,
        user_id=user_data.sub,
        event_topic=kafka_settings.SERVICE_USER_PUBLICATION_TOPIC,
    )
    raise_http_exception_from_service_response(service_response)
    return None


@posts_router.get(
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


@posts_router.get(
    "/feed",
    status_code=HTTPStatus.OK,
)
async def get_last_friends_posts(
    user_data: UserTokenData = Depends(get_user_data_access),
    context: Context = Depends(get_context),
) -> list[GetPostServiceResponseSchema]:
    service = PostService(context=context)
    service_response = await service.get_friends_last_posts(
        user_id=user_data.sub,
        user_utils=UserUtils(),
    )
    raise_http_exception_from_service_response(service_response)
    return service_response.result
