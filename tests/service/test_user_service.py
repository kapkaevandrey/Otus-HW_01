import random as rnd
from uuid import uuid4

import pytest
from faker import Faker

from app.core.services import UserService
from app.schemas.dto import UserCreateSchema
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
