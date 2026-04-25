from http import HTTPStatus
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer

from app.apps.api.utils import raise_http_exception_from_service_response
from app.config import auth_settings
from app.core.containers import Context, get_context
from app.core.enums import ScopeType
from app.core.services import AuthService
from app.schemas.services import AuthCheckTokenData, UserTokenData


class HTTPBearerJWTAuthentication(HTTPBearer):
    INVALID_CRED_EXCEPTION = HTTPException(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail="Invalid authentication credentials",
    )

    def __init__(self, *args: Any, scope_check: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.scope_check = scope_check

    async def __call__(self, request: Request, context: Context = Depends(get_context)) -> UserTokenData:  # type: ignore
        service = AuthService(context=context)
        service_response = await service.get_user_auth_token_data_from_headers(
            headers=dict(request.headers),
            auth_data=AuthCheckTokenData(
                header_key=auth_settings.AUTH_HEADER_KEY,
                token_type=auth_settings.AUTH_TOKEN_TYPE,
                public_key=auth_settings.JWT_PUB_KEY,
                alg=auth_settings.JWT_ALG,
            ),
            scope_check=self.scope_check,
        )
        raise_http_exception_from_service_response(service_response)
        return service_response.result


get_user_data_access = HTTPBearerJWTAuthentication(scope_check=ScopeType.ACCESS)
get_user_data_nay = HTTPBearerJWTAuthentication()
