import datetime as dt
from uuid import uuid4

from faker import Faker

from app.core.enums import EventTypes
from app.core.services import PostService, UserUtils
from app.schemas.dto import UserCreateSchema, UserFriendCreateSchema, UserPublicationDto
from app.schemas.services import CachedFeedPostsSchema, GetPostServiceResponseSchema, ServiceEvent


async def test_get_friends_last_posts_returns_cached_feed(context, user_one):
    service = PostService(context)
    cached_post = UserPublicationDto(
        id=uuid4(),
        user_id=uuid4(),
        text=uuid4().hex,
        created_at=dt.datetime.now(tz=dt.UTC),
        updated_at=dt.datetime.now(tz=dt.UTC),
        is_draft=False,
    )
    expected = [GetPostServiceResponseSchema.model_validate(cached_post)]
    cache_key = service.utils.REDIS_USER_FRIENDS_FEED_KEY.format(user_id=user_one.id)
    await context.redis_client.set(
        cache_key,
        CachedFeedPostsSchema(items=[cached_post], ts=dt.datetime.now(tz=dt.UTC)).model_dump_json(),
    )
    service_response = await service.get_friends_last_posts(user_id=user_one.id, user_utils=UserUtils())
    assert service_response.is_success
    assert service_response.result == expected


async def test_recalculate_user_feed_from_post_event_clears_followers_cache(context, faker: Faker):
    uow = context.uow
    users = await uow.user_repo.add_batch(
        [
            UserCreateSchema(
                first_name=faker.first_name(),
                second_name=faker.last_name(),
                birthdate=dt.date(1990, 1, 1),
                password=uuid4().hex,
            )
            for _ in range(3)
        ]
    )
    follower_one, follower_two, author = users
    await uow.user_friends_repo.add_batch(
        [
            UserFriendCreateSchema(user_id=follower_one.id, friend_id=author.id),
            UserFriendCreateSchema(user_id=follower_two.id, friend_id=author.id),
        ]
    )
    service = PostService(context)
    cached_post = UserPublicationDto(
        id=uuid4(),
        user_id=author.id,
        text=uuid4().hex,
        created_at=dt.datetime.now(tz=dt.UTC),
        updated_at=dt.datetime.now(tz=dt.UTC),
        is_draft=False,
    )
    for follower in (follower_one, follower_two):
        await context.redis_client.set(
            service.utils.REDIS_USER_FRIENDS_FEED_KEY.format(user_id=follower.id),
            CachedFeedPostsSchema(items=[cached_post], ts=dt.datetime.now(tz=dt.UTC)).model_dump_json(),
        )
    service_response = await service.recalculate_user_feed_from_event(
        schema=ServiceEvent(
            event_type=EventTypes.ADD_USER_PUBLICATION,
            data=cached_post.model_dump(mode="json"),
        ),
        user_utils=UserUtils(),
        ts_ms=int(dt.datetime.now(tz=dt.UTC).timestamp() * 1000),
    )
    assert service_response.is_success
    assert await service.utils.get_cached_user_feed(follower_one.id, context.redis_client) is None
    assert await service.utils.get_cached_user_feed(follower_two.id, context.redis_client) is None
