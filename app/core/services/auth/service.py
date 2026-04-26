from functools import cached_property
from http import HTTPStatus
from typing import Any

from app.core.services.base import BaseService, async_use_case
from app.exceptions import BaseServiceError
from app.schemas.services import AuthCheckTokenData, BaseServiceResponse, UserTokenData

from .utils import AuthUtils


class AuthService(BaseService):
    @cached_property
    def utils(self) -> AuthUtils:
        return AuthUtils()

    @async_use_case()
    async def get_user_auth_token_data_from_headers(
        self, headers: dict[str, Any], auth_data: AuthCheckTokenData, scope_check: str | None = None
    ) -> BaseServiceResponse[UserTokenData]:
        response = BaseServiceResponse[UserTokenData]()
        token = self.utils.get_token_for_headers(headers, auth_data)
        user_data = self.utils.get_user_data_from_jwt(token, auth_data.alg, auth_data.public_key)
        if scope_check and scope_check != user_data.scope:
            raise BaseServiceError(
                status=HTTPStatus.UNAUTHORIZED,
                error_message=self.utils.INVALID_JWT_SCOPE_MESSAGE,
            )
        response.result = user_data
        return response
