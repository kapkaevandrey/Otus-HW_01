from http import HTTPStatus
from string import ascii_letters, ascii_uppercase, digits
from uuid import UUID, uuid4

import bcrypt

from app.core.enums import ScopeType, UserType
from app.core.repositories import UnitOfWork
from app.core.services.utils import ServiceUtils
from app.exceptions import BaseServiceError
from app.schemas.dto import UserTokenCreateSchema, UserTokenDto


class AuthUtils(ServiceUtils):
    PASSWORD_MISMATCH_ERROR = "Password mismatch"
    WRONG_PASSWORD = "Не верное значение пароля"
    DEFAULT_AVAILABLE_SYMBOLS = set(ascii_letters + digits + ",.%$@-")
    DEFAULT_NEED_SYMBOLS = [set(ascii_uppercase), set(",.%$@-"), set(digits)]

    @staticmethod
    def get_hash_password(password: str) -> str:
        return (bcrypt.hashpw(password.encode(), bcrypt.gensalt())).decode()

    def check_password(self, password: str, hashed_password: str) -> None:
        if self.get_hash_password(password) != hashed_password:
            raise BaseServiceError(
                status=HTTPStatus.BAD_REQUEST,
                error_message="Password mismatch",
            )

    @staticmethod
    async def get_or_update_user_token(user_id: UUID, scope: ScopeType, uow: UnitOfWork) -> UserTokenDto:
        user_token = await uow.token_repo.get({"id": user_id})
        if not user_token:
            user_token = await uow.token_repo.add(
                UserTokenCreateSchema(token=uuid4(), scope=scope, user_id=user_id, user_type=UserType.USER)
            )
        return user_token

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
