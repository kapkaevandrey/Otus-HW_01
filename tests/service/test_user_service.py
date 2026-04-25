import datetime as dt
import random as rnd
from http import HTTPStatus
from uuid import uuid4

import pytest
from faker import Faker

from app.core.services import UserService
from app.schemas.dto import UserCreateSchema, UserFriendCreateSchema
from app.schemas.services import GetUserServiceResponse


@pytest.mark.parametrize("tries", list(range(10)))
async def test_search_user(context, faker: Faker, tries: int):
    first_names = [faker.first_name() for _ in range(50)]
    second_names = [faker.last_name() for _ in range(50)]
    data = [
        UserCreateSchema(first_name=f, second_name=s, birthdate=faker.date_time().date(), password=uuid4().hex)
        for f in first_names
        for s in second_names
    ]
    users = await context.uow.user_repo.add_batch(data)
    user = rnd.choice(users)
    search_first_name = user.first_name[: len(user.first_name) // 2]
    search_second_name = user.second_name[: len(user.second_name) // 2]
    founded = [
        el
        for el in users
        if el.first_name.startswith(search_first_name) and el.second_name.startswith(search_second_name)
    ]
    assert len(founded) != 0
    service = UserService(context)
    service_response = await service.search_users(first_name=search_first_name, second_name=search_second_name)
    assert service_response.is_success
    assert len(service_response.result) == len(founded)
    founded_map = {el.id: el for el in founded}
    for el in sorted(service_response.result, key=lambda el: el.id):
        assert GetUserServiceResponse.model_validate(founded_map[el.id]) == el


@pytest.mark.parametrize("already_exists", (True, False))
async def test_add_friend(context, faker: Faker, already_exists):
    uow = context.uow
    data = [
        UserCreateSchema(
            first_name=faker.first_name(),
            second_name=faker.last_name(),
            birthdate=dt.date.today(),
            password="some_password",
        )
        for _ in range(2)
    ]
    user, friend = await uow.user_repo.add_batch(data)
    if already_exists:
        await uow.user_friends_repo.add(UserFriendCreateSchema(user_id=user.id, friend_id=friend.id))
    service = UserService(context)
    service_response = await service.add_to_friends(user_id=user.id, friend_id=friend.id, event_topic="topic")
    assert service_response.is_success
    assert service_response.status == HTTPStatus.CREATED
    assert await uow.user_friends_repo.exists({"user_id": user.id, "friend_id": friend.id})


async def test_add_friend_user_not_found(context, faker: Faker):
    uow = context.uow
    data = [
        UserCreateSchema(
            first_name=faker.first_name(),
            second_name=faker.last_name(),
            birthdate=dt.date.today(),
            password="some_password",
        )
        for _ in range(2)
    ]
    user, friend = await uow.user_repo.add_batch(data)
    service = UserService(context)
    service_response = await service.add_to_friends(user_id=uuid4(), friend_id=friend.id, event_topic="topic")
    assert service_response.is_success is False
    assert service_response.status == HTTPStatus.NOT_FOUND
    assert service_response.error_message == service.utils.USER_NOT_FOUND_MESSAGE


async def test_friend_not_found(context, faker: Faker):
    uow = context.uow
    data = [
        UserCreateSchema(
            first_name=faker.first_name(),
            second_name=faker.last_name(),
            birthdate=dt.date.today(),
            password="some_password",
        )
        for _ in range(2)
    ]
    user, friend = await uow.user_repo.add_batch(data)
    service = UserService(context)
    service_response = await service.add_to_friends(user_id=user.id, friend_id=uuid4(), event_topic="topic")
    assert service_response.is_success is False
    assert service_response.status == HTTPStatus.NOT_FOUND
    assert service_response.error_message == service.utils.USER_NOT_FOUND_MESSAGE


async def test_remove_friend(context, faker: Faker):
    uow = context.uow
    data = [
        UserCreateSchema(
            first_name=faker.first_name(),
            second_name=faker.last_name(),
            birthdate=dt.date.today(),
            password="some_password",
        )
        for _ in range(2)
    ]
    user, friend = await uow.user_repo.add_batch(data)
    await uow.user_friends_repo.add(UserFriendCreateSchema(user_id=user.id, friend_id=friend.id))
    service = UserService(context)
    service_response = await service.remove_from_friends(user_id=user.id, friend_id=friend.id, event_topic="topic")
    assert service_response.is_success is True
    assert service_response.status == HTTPStatus.NO_CONTENT
    assert (await uow.user_friends_repo.exists(where_params={"friend_id": friend.id, "user_id": user.id})) is False


async def test_remove_friend_not_found(context, faker: Faker):
    uow = context.uow
    data = [
        UserCreateSchema(
            first_name=faker.first_name(),
            second_name=faker.last_name(),
            birthdate=dt.date.today(),
            password="some_password",
        )
        for _ in range(2)
    ]
    user, friend = await uow.user_repo.add_batch(data)
    service = UserService(context)
    service_response = await service.remove_from_friends(user_id=uuid4(), friend_id=friend.id, event_topic="topic")
    assert service_response.is_success is False
    assert service_response.status == HTTPStatus.NOT_FOUND
