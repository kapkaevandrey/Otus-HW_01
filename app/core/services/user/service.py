from functools import cached_property
from http import HTTPStatus
from uuid import UUID

from app.config import AuthSettings
from app.core.enums import ScopeType
from app.core.services.auth import AuthUtils
from app.core.services.base import BaseService, async_use_case
from app.schemas.dto import UserCreateSchema, UserFriendCreateSchema, UserFriendDto
from app.schemas.services import (
    AccessRefreshServiceResponse,
    AuthTokenInfo,
    BaseServiceResponse,
    GetUserServiceResponse,
    RegisterUserData,
    RegisterUserServiceResponse,
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
        self, *, friend_id: UUID, auth_header: str, auth_info: AuthTokenInfo, auth_utils: AuthUtils
    ) -> BaseServiceResponse[UserFriendDto]:
        response = BaseServiceResponse[UserFriendDto](status=HTTPStatus.CREATED)
        user_data = auth_utils.get_user_data_from_header_string(
            auth_header=auth_header, auth_info=auth_info, scope_check=ScopeType.ACCESS
        )
        async with self.context.uow.transaction() as uow:
            data = UserFriendCreateSchema(user_id=user_data.sub, friend_id=friend_id)
            await self.utils.check_can_add_friends_data(data, uow)
            if user_friend := await uow.user_friends_repo.get(data.model_dump()):
                self.logger.info("Friend already added", extra={"user_id": user_data.sub, "friend_id": friend_id})
            else:
                user_friend = await uow.user_friends_repo.add(data)
            response.result = user_friend
        return response

    @async_use_case()
    async def remove_from_friends(
        self, *, friend_id: UUID, auth_header: str, auth_info: AuthTokenInfo, auth_utils: AuthUtils
    ) -> BaseServiceResponse[UserFriendDto]:
        response = BaseServiceResponse[UserFriendDto](status=HTTPStatus.NO_CONTENT)
        user_data = auth_utils.get_user_data_from_header_string(
            auth_header=auth_header, auth_info=auth_info, scope_check=ScopeType.ACCESS
        )
        async with self.context.uow.transaction() as uow:
            await self.utils.get_user_friend(user_data.sub, friend_id, uow)
            response.result = await uow.user_friends_repo.remove({"user_id": user_data.sub, "friend_id": friend_id})
        return response
