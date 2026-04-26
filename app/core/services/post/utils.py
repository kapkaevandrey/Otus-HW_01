import datetime as dt
from http import HTTPStatus
from uuid import UUID

from app.core.clients import RedisClient
from app.core.repositories import UnitOfWork
from app.core.services.utils import ServiceUtils
from app.exceptions import BaseServiceError
from app.schemas.dto import UserPublicationDto
from app.schemas.services import CachedFeedPostsSchema


class PostUtils(ServiceUtils):
    USER_POST_NOT_FOUNDED = "Post for user not founded"
    POST_NOT_FOUNDED = "Post not founded"

    REDIS_USER_FRIENDS_FEED_KEY = "friends_posts:{user_id}"
    REDIS_USER_FRIENDS_FEED_CALCULATE_CACHE_KEY = "friends_posts:{user_id}:calculate"

    async def get_user_post(self, user_id: UUID, post_id: UUID, uow: UnitOfWork) -> UserPublicationDto:
        if not (post := await uow.user_publication_repo.get({"id": post_id, "user_id": user_id})):
            raise BaseServiceError(
                status=HTTPStatus.NOT_FOUND,
                error_message=self.USER_POST_NOT_FOUNDED,
                error_details={
                    "user_id": str(user_id),
                    "post_id": str(post_id),
                },
            )
        return post

    async def get_post_by_id(self, post_id: UUID, uow: UnitOfWork) -> UserPublicationDto:
        if not (post := await uow.user_publication_repo.get({"id": post_id})):
            raise BaseServiceError(
                status=HTTPStatus.NOT_FOUND,
                error_message=self.USER_POST_NOT_FOUNDED,
                error_details={
                    "post_id": str(post_id),
                },
            )
        return post

    async def get_cached_user_feed(self, user_id: UUID, redis_client: RedisClient) -> CachedFeedPostsSchema | None:
        key = self.REDIS_USER_FRIENDS_FEED_KEY.format(user_id=user_id)
        data = await redis_client.get(key)
        return CachedFeedPostsSchema.model_validate_json(data) if data else None

    async def is_cache_calculated(self, user_id: UUID, redis_client: RedisClient) -> int:
        key = self.REDIS_USER_FRIENDS_FEED_CALCULATE_CACHE_KEY.format(user_id=user_id)
        ttl = await redis_client.ttl(key)
        return max(ttl, 0)

    async def clear_followers_cache(self, users_ids: list[UUID], redis_client: RedisClient) -> None:
        keys = [self.REDIS_USER_FRIENDS_FEED_KEY.format(user_id=user_id) for user_id in users_ids]
        if keys:
            await redis_client.delete(*keys)

    async def set_feed_cache(
        self, user_id: UUID, posts: list[UserPublicationDto], ts: dt.datetime, redis_client: RedisClient, ttl_block: int
    ) -> None:
        if not posts or await self.is_cache_calculated(user_id, redis_client):
            return
        block_key = self.REDIS_USER_FRIENDS_FEED_CALCULATE_CACHE_KEY.format(user_id=user_id)
        cache_key = self.REDIS_USER_FRIENDS_FEED_KEY.format(user_id=user_id)
        await redis_client.set(block_key, 1, ex=ttl_block)
        await redis_client.set(cache_key, CachedFeedPostsSchema(items=posts, ts=ts).model_dump_json())
        await redis_client.delete(block_key)
