from functools import cached_property
from uuid import UUID

from app.core.enums import ScopeType
from app.core.services.auth import AuthUtils
from app.core.services.base import BaseService, async_use_case
from app.schemas.dto import UserCreateSchema
from app.schemas.services import (
    AuthUserServiceResponse,
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
        async with self.context.uow.transaction() as uow:
            dto = await self.utils.get_user_by_id(user_id, uow)
            response.result = GetUserServiceResponse.model_validate(dto)
        return response

    @async_use_case()
    async def login_user(
        self, user_id: UUID, password: str, auth_utils: AuthUtils
    ) -> BaseServiceResponse[AuthUserServiceResponse]:
        response = BaseServiceResponse[AuthUserServiceResponse]()
        async with self.context.uow.transaction() as uow:
            dto = await self.utils.get_user_by_id(user_id, uow)
            auth_utils.check_password(password, dto.password)
            token = await auth_utils.get_or_update_user_token(user_id, ScopeType.ACCESS, uow)
            response.result = AuthUserServiceResponse(token=token.token)
        return response
