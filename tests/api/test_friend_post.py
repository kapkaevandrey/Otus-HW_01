from http import HTTPStatus

from httpx import AsyncClient

from app.apps.api.auth import get_user_data_access
from app.core.enums import ScopeType
from app.schemas.dto import UserFriendCreateSchema, UserPublicationCreateSchema
from app.schemas.services import UserTokenData
from app.server import app


def set_user_access_override(user_id):
    app.dependency_overrides[get_user_data_access] = lambda: UserTokenData(sub=user_id, scope=ScopeType.ACCESS)


def clear_user_access_override():
    app.dependency_overrides.pop(get_user_data_access, None)


async def test_healthz(client: AsyncClient):
    url = app.url_path_for("readiness_probe")
    response = await client.get(url)
    assert response.status_code == HTTPStatus.OK


async def test_livez(client: AsyncClient):
    url = app.url_path_for("liveness_probe")
    response = await client.get(url)
    assert response.status_code == HTTPStatus.OK


async def test_add_to_friends_api(client: AsyncClient, user_one, user_two):
    set_user_access_override(user_one.id)
    try:
        url = app.url_path_for("add_to_friends", user_id=str(user_two.id))
        response = await client.put(url)
    finally:
        clear_user_access_override()
    assert response.status_code == HTTPStatus.OK


async def test_remove_from_friends_api(client: AsyncClient, context, user_one, user_two):
    await context.uow.user_friends_repo.add(UserFriendCreateSchema(user_id=user_one.id, friend_id=user_two.id))
    set_user_access_override(user_one.id)
    try:
        url = app.url_path_for("remove_from_friends", user_id=str(user_two.id))
        response = await client.delete(url)
    finally:
        clear_user_access_override()
    assert response.status_code == HTTPStatus.OK


async def test_create_post_api(client: AsyncClient, user_one):
    set_user_access_override(user_one.id)
    try:
        url = app.url_path_for("add_new_post")
        response = await client.post(url, json={"text": "hello from test"})
    finally:
        clear_user_access_override()
    assert response.status_code == HTTPStatus.OK


async def test_update_post_api(client: AsyncClient, context, user_one):
    post = await context.uow.user_publication_repo.add(
        UserPublicationCreateSchema(user_id=user_one.id, text="old text", is_draft=False)
    )
    set_user_access_override(user_one.id)
    try:
        url = app.url_path_for("update_post")
        response = await client.put(url, json={"id": str(post.id), "text": "new text"})
    finally:
        clear_user_access_override()
    assert response.status_code == HTTPStatus.OK
    assert response.json()["text"] == "new text"


async def test_get_post_api(client: AsyncClient, context, user_one):
    post = await context.uow.user_publication_repo.add(
        UserPublicationCreateSchema(user_id=user_one.id, text="get text", is_draft=False)
    )
    url = app.url_path_for("get_post", post_id=str(post.id))
    response = await client.get(url)
    assert response.status_code == HTTPStatus.OK


async def test_remove_post_api(client: AsyncClient, context, user_one):
    post = await context.uow.user_publication_repo.add(
        UserPublicationCreateSchema(user_id=user_one.id, text="remove me", is_draft=False)
    )
    set_user_access_override(user_one.id)
    try:
        url = app.url_path_for("remove_post", post_id=str(post.id))
        response = await client.delete(url)
    finally:
        clear_user_access_override()
    assert response.status_code == HTTPStatus.NO_CONTENT


async def test_get_last_friends_posts_api(client: AsyncClient, context, user_one, user_two):
    await context.uow.user_friends_repo.add(UserFriendCreateSchema(user_id=user_one.id, friend_id=user_two.id))
    post = await context.uow.user_publication_repo.add(
        UserPublicationCreateSchema(user_id=user_two.id, text="friend post", is_draft=False)
    )
    set_user_access_override(user_one.id)
    try:
        url = app.url_path_for("get_last_friends_posts")
        response = await client.get(url)
    finally:
        clear_user_access_override()
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == str(post.id)
