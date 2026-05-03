from http import HTTPStatus
from uuid import UUID

import jwt
from httpx import AsyncClient

from app.config import auth_settings
from app.core.enums import ScopeType
from app.schemas.services import UserTokenData
from app.server import app


def get_access_headers(user_id: UUID) -> dict[str, str]:
    payload = UserTokenData(sub=user_id, scope=ScopeType.ACCESS).model_dump(mode="json")
    token = jwt.encode(payload=payload, key=auth_settings.JWT_PRIVATE_KEY, algorithm=auth_settings.JWT_ALG)
    return {"Authorization": f"{auth_settings.AUTH_TOKEN_TYPE} {token}"}


async def test_send_message_to_user_api(client: AsyncClient, user_one, user_two):
    url = app.url_path_for("send_message_to_user", user_id=str(user_two.id))
    response = await client.post(
        url,
        json={"text": "hello"},
        headers=get_access_headers(user_one.id),
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["sender_id"] == str(user_one.id)
    assert data["conversation_type"] == "direct"


async def test_send_message_to_self_api(client: AsyncClient, user_one):
    url = app.url_path_for("send_message_to_user", user_id=str(user_one.id))
    response = await client.post(
        url,
        json={"text": "self message"},
        headers=get_access_headers(user_one.id),
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_get_users_dialog_api(client: AsyncClient, user_one, user_two):
    send_url = app.url_path_for("send_message_to_user", user_id=str(user_two.id))
    await client.post(
        send_url,
        json={"text": "message one"},
        headers=get_access_headers(user_one.id),
    )
    await client.post(
        app.url_path_for("send_message_to_user", user_id=str(user_one.id)),
        json={"text": "message two"},
        headers=get_access_headers(user_two.id),
    )

    list_url = app.url_path_for("get_users_dialog", user_id=str(user_two.id))
    response = await client.get(list_url, headers=get_access_headers(user_one.id))
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == 2
    assert {item["text"] for item in data} == {"message one", "message two"}
