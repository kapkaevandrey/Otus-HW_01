import datetime as dt
from uuid import uuid4

import bcrypt
import pytest

from app.core.repositories import UnitOfWork
from app.schemas.dto import UserCreateSchema, UserDto


@pytest.fixture
def user_one_real_password():
    return "RobocopDetroit1,"


@pytest.fixture
async def user_one(context, user_one_real_password) -> UserDto:
    return await context.uow.user_repo.add(
        UserCreateSchema(
            first_name="Alex",
            second_name="Murphy",
            biography="Cop",
            birthdate=dt.date(1990, 1, 1),
            password=(bcrypt.hashpw(user_one_real_password.encode(), bcrypt.gensalt())).decode(),
        )
    )


@pytest.fixture
async def user_two(context, user_one_real_password) -> UserDto:
    return await context.uow.user_repo.add(
        UserCreateSchema(
            first_name="Bruce",
            second_name="Wayne",
            biography="Bat",
            birthdate=dt.date(1987, 1, 1),
            password=(bcrypt.hashpw(user_one_real_password.encode(), bcrypt.gensalt())).decode(),
        )
    )


@pytest.fixture
async def generate_user():
    async def generator(uow: UnitOfWork, amount) -> list[UserDto]:
        data = [
            UserCreateSchema(
                first_name=uuid4().hex,
                second_name=uuid4().hex,
                birthdate=dt.date(1987, 1, 1),
                password=uuid4().hex,
            )
            for _ in range(amount)
        ]
        return await uow.user_repo.add_batch(data)

    return generator
