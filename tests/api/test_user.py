import datetime as dt
from http import HTTPStatus
from uuid import uuid4

from httpx import AsyncClient

from app.schemas.services import RegisterUserData
from app.server import app


async def test_create_user(client: AsyncClient):
    url = app.url_path_for("register_user")
    data = RegisterUserData(
        first_name="John",
        second_name="Doe",
        birthdate=dt.date(1990, 1, 1),
        city="New York",
        password="Qwerty1,",
    )
    response = await client.post(url, json=data.model_dump(mode="json"))
    assert response.status_code == HTTPStatus.OK


async def test_create_user_wrong_password(client: AsyncClient):
    url = app.url_path_for("register_user")
    response = await client.post(
        url,
        json={
            "first_name": "John",
            "second_name": "Doe",
            "birthdate": "1990-01-01",
            "city": "New York",
            "password": "q",
        },
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_get_user_not_found(client: AsyncClient):
    url = app.url_path_for("get_user", user_id=str(uuid4()))
    response = await client.get(url)
    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_get_user(client: AsyncClient, user_one):
    url = app.url_path_for("get_user", user_id=str(user_one.id))
    response = await client.get(url)
    assert response.status_code == HTTPStatus.OK
