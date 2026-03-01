from http import HTTPStatus
from uuid import uuid4

from httpx import AsyncClient

from app.server import app


async def test_login_user_not_found(client: AsyncClient):
    url = app.url_path_for("login_user")
    response = await client.post(url, json={"id": str(uuid4()), "password": "asdf"})
    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_login_user_success(client: AsyncClient, user_one, user_one_real_password):
    url = app.url_path_for("login_user")
    response = await client.post(url, json={"id": str(user_one.id), "password": user_one_real_password})
    assert response.status_code == HTTPStatus.OK
