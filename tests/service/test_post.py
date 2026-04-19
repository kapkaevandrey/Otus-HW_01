import datetime as dt
import random as rnd
from http import HTTPStatus
from uuid import uuid4

import jwt
from faker import Faker

from app.core.enums import ScopeType
from app.core.services import AuthUtils, PostService, UserUtils
from app.schemas.dto import UserFriendCreateSchema, UserPublicationCreateSchema
from app.schemas.services import (
    AuthTokenInfo,
    GetPostServiceResponseSchema,
    PostCreateServiceSchema,
    PostUpdateServiceSchema,
)


async def test_add_post(context, faker: Faker, user_one):
    uow = context.uow
    post_data = PostCreateServiceSchema(text=faker.text())
    auth_info = AuthTokenInfo(alg="HS256", public_key="secret", token_type="Bearer")
    token = jwt.encode(
        algorithm="HS256", payload={"sub": user_one.id.hex, "scope": ScopeType.ACCESS}, key=auth_info.public_key
    )
    service = PostService(context)
    service_response = await service.create_post(
        data=post_data,
        auth_header=f"{auth_info.token_type} {token}",
        auth_info=auth_info,
        auth_utils=AuthUtils(),
        user_utils=UserUtils(),
    )
    assert service_response.is_success
    assert service_response.status == HTTPStatus.CREATED
    assert uow.user_publication_repo.exists({"user_id": user_one.id})


async def test_add_post_user_not_found(context, faker: Faker):
    post_data = PostCreateServiceSchema(text=faker.text())
    auth_info = AuthTokenInfo(alg="HS256", public_key="secret", token_type="Bearer")
    token = jwt.encode(
        algorithm="HS256", payload={"sub": uuid4().hex, "scope": ScopeType.ACCESS}, key=auth_info.public_key
    )
    service = PostService(context)
    service_response = await service.create_post(
        data=post_data,
        auth_header=f"{auth_info.token_type} {token}",
        auth_info=auth_info,
        auth_utils=AuthUtils(),
        user_utils=UserUtils(),
    )
    assert service_response.is_success is False
    assert service_response.status == HTTPStatus.NOT_FOUND


async def test_update_post(context, faker: Faker, user_one):
    uow = context.uow
    post = await uow.user_publication_repo.add(
        UserPublicationCreateSchema(text=faker.text(), user_id=user_one.id, is_draft=False)
    )
    update_data = PostUpdateServiceSchema(text=uuid4().hex, id=post.id)
    auth_info = AuthTokenInfo(alg="HS256", public_key="secret", token_type="Bearer")
    token = jwt.encode(
        algorithm="HS256", payload={"sub": user_one.id.hex, "scope": ScopeType.ACCESS}, key=auth_info.public_key
    )
    service = PostService(context)
    service_response = await service.update_post(
        data=update_data,
        auth_header=f"{auth_info.token_type} {token}",
        auth_info=auth_info,
        auth_utils=AuthUtils(),
    )
    assert service_response.is_success is True
    assert service_response.status == HTTPStatus.OK
    res = service_response.result
    assert res.text == update_data.text


async def test_update_other_user_post(context, faker: Faker, user_one, user_two):
    uow = context.uow
    post = await uow.user_publication_repo.add(
        UserPublicationCreateSchema(text=faker.text(), user_id=user_two.id, is_draft=False)
    )
    update_data = PostUpdateServiceSchema(text=uuid4().hex, id=post.id)
    auth_info = AuthTokenInfo(alg="HS256", public_key="secret", token_type="Bearer")
    token = jwt.encode(
        algorithm="HS256", payload={"sub": user_one.id.hex, "scope": ScopeType.ACCESS}, key=auth_info.public_key
    )
    service = PostService(context)
    service_response = await service.update_post(
        data=update_data,
        auth_header=f"{auth_info.token_type} {token}",
        auth_info=auth_info,
        auth_utils=AuthUtils(),
    )
    assert service_response.is_success is False
    assert service_response.status == HTTPStatus.NOT_FOUND
    assert service_response.error_message == service.utils.USER_POST_NOT_FOUNDED


async def test_remove_user_post(context, faker: Faker, user_one):
    uow = context.uow
    post = await uow.user_publication_repo.add(
        UserPublicationCreateSchema(text=faker.text(), user_id=user_one.id, is_draft=False)
    )
    auth_info = AuthTokenInfo(alg="HS256", public_key="secret", token_type="Bearer")
    token = jwt.encode(
        algorithm="HS256", payload={"sub": user_one.id.hex, "scope": ScopeType.ACCESS}, key=auth_info.public_key
    )
    service = PostService(context)
    service_response = await service.remove_post(
        post_id=post.id,
        auth_header=f"{auth_info.token_type} {token}",
        auth_info=auth_info,
        auth_utils=AuthUtils(),
    )
    assert service_response.is_success is True
    assert service_response.status == HTTPStatus.NO_CONTENT
    assert await uow.user_publication_repo.count() == 0


async def test_remove_other_user_post(context, faker: Faker, user_one, user_two):
    uow = context.uow
    post = await uow.user_publication_repo.add(
        UserPublicationCreateSchema(text=faker.text(), user_id=user_two.id, is_draft=False)
    )
    auth_info = AuthTokenInfo(alg="HS256", public_key="secret", token_type="Bearer")
    token = jwt.encode(
        algorithm="HS256", payload={"sub": user_one.id.hex, "scope": ScopeType.ACCESS}, key=auth_info.public_key
    )
    service = PostService(context)
    service_response = await service.remove_post(
        post_id=post.id,
        auth_header=f"{auth_info.token_type} {token}",
        auth_info=auth_info,
        auth_utils=AuthUtils(),
    )
    assert service_response.is_success is False
    assert service_response.status == HTTPStatus.NOT_FOUND
    assert await uow.user_publication_repo.count() == 1


async def test_friends_feeds(user_one, context, generate_user):
    uow = context.uow
    auth_info = AuthTokenInfo(alg="HS256", public_key="secret", token_type="Bearer")
    token = jwt.encode(
        algorithm="HS256", payload={"sub": user_one.id.hex, "scope": ScopeType.ACCESS}, key=auth_info.public_key
    )
    start_time = dt.datetime(year=2000, month=1, minute=1, day=1, tzinfo=dt.UTC)
    timestamps = [start_time + dt.timedelta(minutes=i) for i in range(100_000)]
    users = await generate_user(uow, 1000)
    friends = rnd.sample(users, 50)
    friends_ids = [user.id for user in friends]
    await uow.user_friends_repo.add_batch(
        [UserFriendCreateSchema(user_id=user_one.id, friend_id=friend.id) for friend in friends]
    )
    posts_data = []
    counter = 0
    for user in users:
        for _ in range(rnd.randint(5, 40)):
            posts_data.append(
                UserPublicationCreateSchema(
                    user_id=user.id,
                    text=uuid4().hex,
                    is_draft=False,
                    created_at=timestamps[counter],
                )
            )
            counter += 1
    posts = await uow.user_publication_repo.add_batch(posts_data)
    friends_posts = [el for el in posts if el.user_id in friends_ids]
    friends_posts.sort(key=lambda x: x.created_at, reverse=True)
    expected = [
        GetPostServiceResponseSchema.model_validate(el) for el in friends_posts[: PostService.FEED_DEFAULT_SIZE]
    ]
    service = PostService(context)
    service_response = await service.get_friends_last_posts(
        auth_header=f"{auth_info.token_type} {token}",
        auth_info=auth_info,
        auth_utils=AuthUtils(),
        user_utils=UserUtils(),
    )
    assert service_response.is_success
    assert service_response.status == HTTPStatus.OK
    assert service_response.result == expected


async def test_get_post(context, faker: Faker, user_one):
    uow = context.uow
    post = await uow.user_publication_repo.add(
        UserPublicationCreateSchema(text=faker.text(), user_id=user_one.id, is_draft=False)
    )
    service = PostService(context)
    service_response = await service.get_post(
        post_id=post.id,
    )
    assert service_response.is_success is True
    assert service_response.status == HTTPStatus.OK


async def test_get_post_not_found(context, faker: Faker):
    service = PostService(context)
    service_response = await service.get_post(
        post_id=uuid4(),
    )
    assert service_response.is_success is False
    assert service_response.status == HTTPStatus.NOT_FOUND
