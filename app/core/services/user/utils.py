from http import HTTPStatus
from uuid import UUID

from app.core.repositories import UnitOfWork
from app.core.services.utils import ServiceUtils
from app.exceptions import BaseServiceError
from app.schemas.dto import UserDto, UserFriendCreateSchema, UserFriendDto


class UserUtils(ServiceUtils):
    USER_NOT_FOUND_MESSAGE = "User not found"
    CANT_ADD_SELF_TO_FRIENDS_MESSAGE = "Can not add self to friends"
    FRIEND_NOT_FOUNDED = "Friend for user not found"

    async def get_user_by_id(self, user_id: UUID, uow: UnitOfWork) -> UserDto:
        if not (user_dto := await uow.user_repo.get({"id": user_id})):
            raise BaseServiceError(
                status=HTTPStatus.NOT_FOUND,
                error_message=self.USER_NOT_FOUND_MESSAGE,
                error_details={"id": str(user_id)},
            )
        return user_dto

    async def check_can_add_friends_data(self, data: UserFriendCreateSchema, uow: UnitOfWork) -> None:
        if data.user_id == data.friend_id:
            raise BaseServiceError(
                status=HTTPStatus.CONFLICT,
                error_message=self.CANT_ADD_SELF_TO_FRIENDS_MESSAGE,
                error_details={"friend_id": str(data.friend_id), "user_id": str(data.user_id)},
            )
        await self.get_user_by_id(data.user_id, uow)
        await self.get_user_by_id(data.friend_id, uow)

    async def get_user_friend(self, user_id: UUID, friend_id: UUID, uow: UnitOfWork) -> UserFriendDto:
        if not (dto := await uow.user_friends_repo.get({"user_id": user_id, "friend_id": friend_id})):
            raise BaseServiceError(
                status=HTTPStatus.NOT_FOUND,
                error_message=self.FRIEND_NOT_FOUNDED,
                error_details={"friend_id": str(friend_id), "user_id": str(user_id)},
            )
        return dto
