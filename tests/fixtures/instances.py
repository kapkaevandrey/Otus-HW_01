import datetime as dt

import bcrypt
import pytest

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
