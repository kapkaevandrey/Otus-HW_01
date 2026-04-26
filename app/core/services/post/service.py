import asyncio
from functools import cached_property
from http import HTTPStatus
from uuid import UUID

from app.core.enums import EventTypes
from app.core.repositories import JoinCondition, JoinParams, JoinType
from app.core.services.base import BaseService, async_use_case
from app.core.services.user import UserUtils
from app.core.utils import utcnow
from app.exceptions import BaseServiceError
from app.schemas.dto import UserFriendDto, UserPublicationCreateSchema, UserPublicationDto, UserPublicationUpdateSchema
from app.schemas.services import (
    BaseServiceResponse,
    GetPostServiceResponseSchema,
    PostCreateServiceSchema,
    PostUpdateServiceSchema,
    ServiceEvent,
)

from .utils import PostUtils


class PostService(BaseService):
    FEED_DEFAULT_SIZE = 1_000
    RECALCULATE_CACHE_EVENTS: set[EventTypes] = {
        EventTypes.ADD_FRIEND,
        EventTypes.REMOVE_FRIEND,
        EventTypes.ADD_USER_PUBLICATION,
        EventTypes.UPDATE_USER_PUBLICATION,
        EventTypes.REMOVE_USER_PUBLICATION,
    }

    @cached_property
    def utils(self) -> PostUtils:
        return PostUtils()

    @async_use_case()
    async def create_post(
        self, user_id: UUID, data: PostCreateServiceSchema, user_utils: UserUtils, event_topic: str
    ) -> BaseServiceResponse[GetPostServiceResponseSchema]:
        response = BaseServiceResponse[GetPostServiceResponseSchema](status=HTTPStatus.CREATED)
        async with self.context.uow.transaction() as uow:
            user = await user_utils.get_user_by_id(user_id=user_id, uow=uow)
            post = await uow.user_publication_repo.add(
                UserPublicationCreateSchema(text=data.text, is_draft=False, user_id=user.id)
            )
            response.result = GetPostServiceResponseSchema(**post.model_dump())
            event = ServiceEvent(event_type=EventTypes.ADD_USER_PUBLICATION, data=post.model_dump())
            await self.context.kafka_producer.send_message(
                value=event.model_dump(mode="json"),
                key=user_id.hex,
                topic=event_topic,
            )
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
        user_id: UUID,
        data: PostUpdateServiceSchema,
        event_topic: str,
    ) -> BaseServiceResponse[GetPostServiceResponseSchema]:
        response = BaseServiceResponse[GetPostServiceResponseSchema]()
        async with self.context.uow.transaction() as uow:
            post = await self.utils.get_user_post(user_id, data.id, uow)
            upd_post = await uow.user_publication_repo.update(
                {"id": post.id}, UserPublicationUpdateSchema(text=data.text, updated_at=utcnow()), exclude_none=True
            )
            event = ServiceEvent(event_type=EventTypes.UPDATE_USER_PUBLICATION, data=upd_post.model_dump())
            response.result = GetPostServiceResponseSchema(**upd_post.model_dump())
            await self.context.kafka_producer.send_message(
                value=event.model_dump(mode="json"),
                key=user_id.hex,
                topic=event_topic,
            )
        return response

    @async_use_case()
    async def remove_post(
        self,
        user_id: UUID,
        post_id: UUID,
        event_topic: str,
    ) -> BaseServiceResponse[UserPublicationDto]:
        response = BaseServiceResponse[UserPublicationDto](status=HTTPStatus.NO_CONTENT)
        async with self.context.uow.transaction() as uow:
            post = await self.utils.get_user_post(user_id, post_id, uow)
            removed_post = await uow.user_publication_repo.remove({"id": post.id})
            response.result = removed_post
            event = ServiceEvent(event_type=EventTypes.REMOVE_USER_PUBLICATION, data=removed_post.model_dump())
            await self.context.kafka_producer.send_message(
                value=event.model_dump(mode="json"),
                key=user_id.hex,
                topic=event_topic,
            )
        return response

    @async_use_case()
    async def get_friends_last_posts(
        self,
        user_id: UUID,
        user_utils: UserUtils,
    ) -> BaseServiceResponse[GetPostServiceResponseSchema]:
        response = BaseServiceResponse[GetPostServiceResponseSchema]()
        if ttl := await self.utils.is_cache_calculated(user_id, self.context.redis_client):
            await asyncio.sleep(ttl)
        cached_feed = await self.utils.get_cached_user_feed(user_id, self.context.redis_client)
        if cached_feed:
            response.result = [GetPostServiceResponseSchema.model_validate(el) for el in cached_feed.items]
            return response
        posts = await self._get_user_friends_posts_and_cached(user_id, self.FEED_DEFAULT_SIZE, user_utils)
        response.result = [GetPostServiceResponseSchema.model_validate(el) for el in posts]
        return response

    @async_use_case()
    async def recalculate_user_feed_from_event(
        self, schema: ServiceEvent, user_utils: UserUtils, ts_ms: int
    ) -> BaseServiceResponse[None]:
        response = BaseServiceResponse[None](status=HTTPStatus.NO_CONTENT)
        if schema.event_type not in self.RECALCULATE_CACHE_EVENTS:
            raise BaseServiceError(
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                error_message="Recalculate user feed cache is not supported for event",
                error_details={"event": schema.model_dump(mode="json")},
            )
        if schema.event_type in (EventTypes.ADD_FRIEND, EventTypes.REMOVE_FRIEND):
            user_friend = UserFriendDto.model_validate(schema.data)
            data = await self.utils.get_cached_user_feed(user_friend.user_id, self.context.redis_client)
            if data and int(data.ts.timestamp() * 1000) < ts_ms:
                await self._get_user_friends_posts_and_cached(
                    user_id=user_friend.user_id, user_utils=user_utils, size=self.FEED_DEFAULT_SIZE
                )
        elif schema.event_type in (
            EventTypes.UPDATE_USER_PUBLICATION,
            EventTypes.REMOVE_USER_PUBLICATION,
            EventTypes.ADD_USER_PUBLICATION,
        ):
            post = UserPublicationDto.model_validate(schema.data)
            async with self.context.uow.transaction() as uow:
                followers_ids = await uow.user_friends_repo.get_need_fields(
                    fields=["user_id"], where={"friend_id": post.user_id}, mapped=False
                )
                await self.utils.clear_followers_cache(
                    users_ids=[row[0] for row in followers_ids], redis_client=self.context.redis_client
                )
        return response

    async def _get_user_friends_posts_and_cached(
        self,
        user_id: UUID,
        size: int,
        user_utils: UserUtils,
    ) -> list[UserPublicationDto]:
        async with self.context.uow.transaction() as uow:
            user = await user_utils.get_user_by_id(user_id=user_id, uow=uow)
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
                joins=join_params, order_fields=["created_at__desc"], limit=size
            )
            await self.utils.set_feed_cache(
                user_id=user_id, posts=posts, redis_client=self.context.redis_client, ttl_block=1, ts=utcnow()
            )
        return posts
