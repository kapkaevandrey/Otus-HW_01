import datetime as dt
from http import HTTPStatus
from string import ascii_letters, ascii_uppercase, digits
from typing import Any
from uuid import UUID

import bcrypt
import jwt
from pydantic import ValidationError

from app.config import AuthSettings
from app.core.enums import ScopeType
from app.core.services.utils import ServiceUtils
from app.exceptions import BaseServiceError
from app.schemas.services import (
    AccessRefreshServiceResponse,
    AuthCheckTokenData,
    TokenSchema,
    UserTokenData,
)


class AuthUtils(ServiceUtils):
    PASSWORD_MISMATCH_ERROR = "Password mismatch"
    WRONG_PASSWORD = "Не верное значение пароля"
    DEFAULT_AVAILABLE_SYMBOLS = set(ascii_letters + digits + ",.%$@-")
    DEFAULT_NEED_SYMBOLS = [set(ascii_uppercase), set(",.%$@-"), set(digits)]
    USER_NOT_AUTHORIZED_MESSAGE = "User is not authorized"
    WRONG_TOKEN_TYPE_MESSAGE = "Wrong token type"
    TOKEN_REQUIRED_MESSAGE = "Token required"
    INVALID_TOKEN_FORMAT_MESSAGE = "Invalid token format {error}"
    INVALID_JWT_TOKEN_MESSAGE = "Invalid JWT token"
    INVALID_JWT_PAYLOAD_MESSAGE = "Invalid JWT payload"
    INVALID_JWT_SCOPE_MESSAGE = "Invalid JWT scope"
    INVALID_TOKEN_SCHEMA_MESSAGE = "Token or scheme is not valid"

    @staticmethod
    def get_hash_password(password: str) -> str:
        return (bcrypt.hashpw(password.encode(), bcrypt.gensalt())).decode()

    def check_password(self, password: str, hashed_password: str) -> None:
        if not bcrypt.checkpw(password.encode(), hashed_password.encode()):
            raise BaseServiceError(
                status=HTTPStatus.BAD_REQUEST,
                error_message=self.PASSWORD_MISMATCH_ERROR,
            )

    @staticmethod
    def get_access_refresh_token(user_id: UUID, settings: AuthSettings) -> AccessRefreshServiceResponse:
        now = dt.datetime.now(dt.UTC)
        access_exp = now + dt.timedelta(seconds=settings.JWT_ACCESS_EXP_SECONDS)
        refresh_exp = now + dt.timedelta(seconds=settings.JWT_REFRESH_EXP_SECONDS)
        jwt_data = {
            "sub": str(user_id),
            "scope": ScopeType.ACCESS,
            "exp": access_exp,
            "iat": dt.datetime.now(),
        }
        access_token = jwt.encode(payload=jwt_data, key=settings.JWT_PRIVATE_KEY, algorithm=settings.JWT_ALG)
        jwt_data["exp"] = refresh_exp
        jwt_data["scope"] = ScopeType.REFRESH
        refresh_token = jwt.encode(payload=jwt_data, key=settings.JWT_PRIVATE_KEY, algorithm=settings.JWT_ALG)
        return AccessRefreshServiceResponse(
            access_token=TokenSchema(
                token=access_token,
                type=settings.AUTH_TOKEN_TYPE,
                scope=ScopeType.ACCESS,
                exp=int(access_exp.timestamp()),
            ),
            refresh_token=TokenSchema(
                token=refresh_token,
                type=settings.AUTH_TOKEN_TYPE,
                scope=ScopeType.REFRESH,
                exp=int(refresh_exp.timestamp()),
            ),
        )

    def check_password_is_correct(
        self,
        password: str,
        min_length: int = 8,
        available_symbols: set[str] | None = None,
        need_symbols_sets: list[set[str]] | None = None,
    ) -> None:
        pass_set = set(password)
        available_symbols = available_symbols or self.DEFAULT_AVAILABLE_SYMBOLS
        need_symbols_sets = need_symbols_sets or self.DEFAULT_NEED_SYMBOLS
        only_available = not bool(pass_set - available_symbols)
        has_needs_symbols = all(bool(pass_set.intersection(need_symbols_set)) for need_symbols_set in need_symbols_sets)
        good_length = len(password) >= min_length
        if has_needs_symbols and good_length and only_available:
            return
        raise BaseServiceError(
            status=HTTPStatus.BAD_REQUEST,
            error_message=self.WRONG_PASSWORD,
        )

    def get_user_data_from_jwt(self, jwt_token: str, alg: str, secret: str | None) -> UserTokenData:
        payload = self._get_jwt_payload(jwt_token, alg, secret)
        try:
            return UserTokenData.model_validate(payload)
        except ValidationError as error:
            self.logger.error(self.INVALID_JWT_PAYLOAD_MESSAGE)
            raise BaseServiceError(
                status=HTTPStatus.UNAUTHORIZED,
                error_message=self.INVALID_JWT_PAYLOAD_MESSAGE,
                error_details={"errors": error.errors()},
            ) from error

    def _get_jwt_payload(self, jwt_token: str, alg: str, secret: str | None) -> dict:
        decode_params: dict[str, Any] = {"key": secret} if secret else {"options": {"verify_signature": False}}
        try:
            decode_params["algorithms"] = alg
            payload = jwt.decode(jwt_token, **decode_params)
            return payload
        except jwt.InvalidTokenError as error:
            error_message = self.INVALID_TOKEN_FORMAT_MESSAGE.format(error=error)
            self.logger.error(error_message)
            raise BaseServiceError(status=HTTPStatus.UNAUTHORIZED, error_message=error_message) from error

    def get_token_for_headers(self, headers: dict[str, str], auth_info: AuthCheckTokenData) -> str:
        raw_token = None
        header_key = auth_info.header_key.strip().lower()
        for key, value in headers.items():
            if key.strip().lower() == header_key:
                raw_token = value
                break
        if not raw_token or not isinstance(raw_token, str):
            raise BaseServiceError(status=HTTPStatus.UNAUTHORIZED, error_message=self.INVALID_JWT_TOKEN_MESSAGE)
        scheme, *token_parts = raw_token.split(" ", 1)
        if scheme != auth_info.token_type or not token_parts:
            raise BaseServiceError(status=HTTPStatus.UNAUTHORIZED, error_message=self.INVALID_TOKEN_SCHEMA_MESSAGE)
        return token_parts[0]
