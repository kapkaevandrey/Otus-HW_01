from http import HTTPStatus
from uuid import UUID

from app.core.repositories import UnitOfWork
from app.core.services.utils import ServiceUtils
from app.exceptions import BaseServiceError
from app.schemas.dto import UserDto


class UserUtils(ServiceUtils):
    USER_NOT_FOUND_MESSAGE = "User not found"

    async def get_user_by_id(self, user_id: UUID, uow: UnitOfWork) -> UserDto:
        if not (user_dto := await uow.user_repo.get({"id": user_id})):
            raise BaseServiceError(
                status=HTTPStatus.NOT_FOUND,
                error_message=self.USER_NOT_FOUND_MESSAGE,
                error_details={"id": str(user_id)},
            )
        return user_dto
