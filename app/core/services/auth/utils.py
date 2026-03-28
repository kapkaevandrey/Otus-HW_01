import datetime as dt
from http import HTTPStatus
from string import ascii_letters, ascii_uppercase, digits
from uuid import UUID

import bcrypt
import jwt

from app.config import AuthSettings
from app.core.enums import ScopeType
from app.core.services.utils import ServiceUtils
from app.exceptions import BaseServiceError
from app.schemas.services import AccessRefreshServiceResponse, TokenSchema


class AuthUtils(ServiceUtils):
    PASSWORD_MISMATCH_ERROR = "Password mismatch"
    WRONG_PASSWORD = "Не верное значение пароля"
    DEFAULT_AVAILABLE_SYMBOLS = set(ascii_letters + digits + ",.%$@-")
    DEFAULT_NEED_SYMBOLS = [set(ascii_uppercase), set(",.%$@-"), set(digits)]

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
