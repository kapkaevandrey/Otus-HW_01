from functools import cached_property
from http import HTTPStatus
from uuid import UUID

from app.config import AuthSettings
from app.core.enums import EventTypes
from app.core.services.auth import AuthUtils
from app.core.services.base import BaseService, async_use_case
from app.schemas.dto import UserCreateSchema, UserFriendCreateSchema, UserFriendDto
from app.schemas.services import (
    AccessRefreshServiceResponse,
    BaseServiceResponse,
    GetUserServiceResponse,
    RegisterUserData,
    RegisterUserServiceResponse,
    ServiceEvent,
)

from .utils import UserUtils


class UserService(BaseService):
    @cached_property
    def utils(self) -> UserUtils:
        return UserUtils()

    @async_use_case()
    async def register_user(
        self, data: RegisterUserData, auth_utils: AuthUtils
    ) -> BaseServiceResponse[RegisterUserServiceResponse]:
        response = BaseServiceResponse[RegisterUserServiceResponse]()
        async with self.context.uow.transaction() as uow:
            dto = await uow.user_repo.add(
                UserCreateSchema(
                    **data.model_dump(exclude={"password"}), password=auth_utils.get_hash_password(data.password)
                )
            )
            response.result = RegisterUserServiceResponse(user_id=dto.id)
        return response

    @async_use_case()
    async def get_user(self, user_id: UUID) -> BaseServiceResponse[GetUserServiceResponse]:
        response = BaseServiceResponse[GetUserServiceResponse]()
        async with self.context.uow.transaction(read_only=True) as uow:
            dto = await self.utils.get_user_by_id(user_id, uow)
            response.result = GetUserServiceResponse.model_validate(dto)
        return response

    @async_use_case()
    async def login_user(
        self, user_id: UUID, password: str, auth_utils: AuthUtils, settings: AuthSettings
    ) -> BaseServiceResponse[AccessRefreshServiceResponse]:
        response = BaseServiceResponse[AccessRefreshServiceResponse]()
        async with self.context.uow.transaction(read_only=True) as uow:
            dto = await self.utils.get_user_by_id(user_id, uow)
            auth_utils.check_password(password, dto.password)
            response.result = auth_utils.get_access_refresh_token(user_id, settings)
        return response

    @async_use_case()
    async def search_users(
        self, first_name: str, second_name: str
    ) -> BaseServiceResponse[list[GetUserServiceResponse]]:
        response = BaseServiceResponse[list[GetUserServiceResponse]]()
        first_name = first_name if first_name.endswith("%") else f"{first_name}%"
        second_name = second_name if second_name.endswith("%") else f"{second_name}%"
        async with self.context.uow.transaction(read_only=True) as uow:
            dtos = await uow.user_repo.get_by_attributes(
                {"first_name__like": first_name, "second_name__like": second_name}
            )
            response.result = [GetUserServiceResponse.model_validate(dto) for dto in dtos]
        return response

    @async_use_case()
    async def add_to_friends(
        self, *, user_id: UUID, friend_id: UUID, event_topic: str
    ) -> BaseServiceResponse[UserFriendDto]:
        response = BaseServiceResponse[UserFriendDto](status=HTTPStatus.CREATED)
        async with self.context.uow.transaction() as uow:
            data = UserFriendCreateSchema(user_id=user_id, friend_id=friend_id)
            await self.utils.check_can_add_friends_data(data, uow)
            if user_friend := await uow.user_friends_repo.get(data.model_dump()):
                self.logger.info("Friend already added", extra={"user_id": user_id, "friend_id": friend_id})
            else:
                user_friend = await uow.user_friends_repo.add(data)
                event = ServiceEvent(
                    event_type=EventTypes.ADD_FRIEND,
                    data=user_friend.model_dump(),
                )
                await self.context.kafka_producer.send_message(
                    key=user_friend.user_id.hex,
                    value=event.model_dump(mode="json"),
                    topic=event_topic,
                )
            response.result = user_friend
        return response

    @async_use_case()
    async def remove_from_friends(
        self, *, user_id: UUID, friend_id: UUID, event_topic: str
    ) -> BaseServiceResponse[UserFriendDto]:
        response = BaseServiceResponse[UserFriendDto](status=HTTPStatus.NO_CONTENT)
        async with self.context.uow.transaction() as uow:
            await self.utils.get_user_friend(user_id, friend_id, uow)
            dto = await uow.user_friends_repo.remove({"user_id": user_id, "friend_id": friend_id})
            response.result = dto
            event = ServiceEvent(
                event_type=EventTypes.REMOVE_FRIEND,
                data=dto.model_dump(),
            )
            await self.context.kafka_producer.send_message(
                key=dto.user_id.hex,
                value=event.model_dump(mode="json"),
                topic=event_topic,
            )
        return response
