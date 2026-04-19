from functools import cached_property
from http import HTTPStatus
from uuid import UUID

from app.core.enums import ScopeType
from app.core.repositories import JoinCondition, JoinParams, JoinType
from app.core.services.auth import AuthUtils
from app.core.services.base import BaseService, async_use_case
from app.core.services.user import UserUtils
from app.core.utils import utcnow
from app.schemas.dto import UserPublicationCreateSchema, UserPublicationDto, UserPublicationUpdateSchema
from app.schemas.services import (
    AuthTokenInfo,
    BaseServiceResponse,
    GetPostServiceResponseSchema,
    PostCreateServiceSchema,
    PostUpdateServiceSchema,
)

from .utils import PostUtils


class PostService(BaseService):
    FEED_DEFAULT_SIZE = 1_000

    @cached_property
    def utils(self) -> PostUtils:
        return PostUtils()

    @async_use_case()
    async def create_post(
        self,
        data: PostCreateServiceSchema,
        auth_header: str,
        auth_info: AuthTokenInfo,
        auth_utils: AuthUtils,
        user_utils: UserUtils,
    ) -> BaseServiceResponse[GetPostServiceResponseSchema]:
        response = BaseServiceResponse[GetPostServiceResponseSchema](status=HTTPStatus.CREATED)
        user_data = auth_utils.get_user_data_from_header_string(
            auth_header=auth_header, auth_info=auth_info, scope_check=ScopeType.ACCESS
        )
        async with self.context.uow.transaction() as uow:
            user = await user_utils.get_user_by_id(user_id=user_data.sub, uow=uow)
            post = await uow.user_publication_repo.add(
                UserPublicationCreateSchema(text=data.text, is_draft=False, user_id=user.id)
            )
            response.result = GetPostServiceResponseSchema(**post.model_dump())
        return response

    @async_use_case()
    async def get_post(
        self,
        post_id: UUID,
    ) -> BaseServiceResponse[GetPostServiceResponseSchema]:
        response = BaseServiceResponse[GetPostServiceResponseSchema]()
        async with self.context.uow.transaction() as uow:
            post = await self.utils.get_post_by_id(post_id, uow)
            response.result = GetPostServiceResponseSchema(**post.model_dump())
        return response

    @async_use_case()
    async def update_post(
        self,
        data: PostUpdateServiceSchema,
        auth_header: str,
        auth_info: AuthTokenInfo,
        auth_utils: AuthUtils,
    ) -> BaseServiceResponse[GetPostServiceResponseSchema]:
        response = BaseServiceResponse[GetPostServiceResponseSchema]()
        user_data = auth_utils.get_user_data_from_header_string(
            auth_header=auth_header, auth_info=auth_info, scope_check=ScopeType.ACCESS
        )
        async with self.context.uow.transaction() as uow:
            post = await self.utils.get_user_post(user_data.sub, data.id, uow)
            upd_post = await uow.user_publication_repo.update(
                {"id": post.id}, UserPublicationUpdateSchema(text=data.text, updated_at=utcnow()), exclude_none=True
            )
            response.result = GetPostServiceResponseSchema(**upd_post.model_dump())
        return response

    @async_use_case()
    async def remove_post(
        self,
        post_id: UUID,
        auth_header: str,
        auth_info: AuthTokenInfo,
        auth_utils: AuthUtils,
    ) -> BaseServiceResponse[UserPublicationDto]:
        response = BaseServiceResponse[UserPublicationDto](status=HTTPStatus.NO_CONTENT)
        user_data = auth_utils.get_user_data_from_header_string(
            auth_header=auth_header, auth_info=auth_info, scope_check=ScopeType.ACCESS
        )
        async with self.context.uow.transaction() as uow:
            post = await self.utils.get_user_post(user_data.sub, post_id, uow)
            removed_post = await uow.user_publication_repo.remove({"id": post.id})
            response.result = removed_post
        return response

    @async_use_case()
    async def get_friends_last_posts(
        self,
        auth_header: str,
        auth_info: AuthTokenInfo,
        auth_utils: AuthUtils,
        user_utils: UserUtils,
    ) -> BaseServiceResponse[GetPostServiceResponseSchema]:
        response = BaseServiceResponse[GetPostServiceResponseSchema]()
        user_data = auth_utils.get_user_data_from_header_string(
            auth_header=auth_header, auth_info=auth_info, scope_check=ScopeType.ACCESS
        )
        async with self.context.uow.transaction() as uow:
            user = await user_utils.get_user_by_id(user_id=user_data.sub, uow=uow)
            join_params = [
                JoinParams(
                    orig_repo=uow.user_publication_repo,
                    joined_repo=uow.user_friends_repo,
                    join_type=JoinType.INNER,
                    on=[JoinCondition(orig="user_id", operator="=", joined="friend_id")],
                    where={"user_id": user.id},
                )
            ]
            posts = await uow.user_publication_repo.get_by_attributes(
                joins=join_params, order_fields=["created_at__desc"], limit=self.FEED_DEFAULT_SIZE
            )
            response.result = [GetPostServiceResponseSchema.model_validate(el) for el in posts]
        return response
