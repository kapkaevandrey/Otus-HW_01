from http import HTTPStatus
from uuid import UUID

from app.core.repositories import UnitOfWork
from app.core.services.utils import ServiceUtils
from app.exceptions import BaseServiceError
from app.schemas.dto import UserPublicationDto


class PostUtils(ServiceUtils):
    USER_POST_NOT_FOUNDED = "Post for user not founded"
    POST_NOT_FOUNDED = "Post not founded"

    async def get_user_post(self, user_id: UUID, post_id: UUID, uow: UnitOfWork) -> UserPublicationDto:
        if not (post := await uow.user_publication_repo.get({"id": post_id, "user_id": user_id})):
            raise BaseServiceError(
                status=HTTPStatus.NOT_FOUND,
                error_message=self.USER_POST_NOT_FOUNDED,
                error_details={
                    "user_id": str(user_id),
                    "post_id": str(post_id),
                },
            )
        return post

    async def get_post_by_id(self, post_id: UUID, uow: UnitOfWork) -> UserPublicationDto:
        if not (post := await uow.user_publication_repo.get({"id": post_id})):
            raise BaseServiceError(
                status=HTTPStatus.NOT_FOUND,
                error_message=self.USER_POST_NOT_FOUNDED,
                error_details={
                    "post_id": str(post_id),
                },
            )
        return post
