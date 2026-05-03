from collections.abc import Awaitable, Callable
from logging import Logger, getLogger
from typing import Any

from app.core.containers import Context
from app.exceptions import BaseServiceError
from app.schemas.services import BaseServiceResponse


logger = getLogger(__name__)


class BaseService:
    def __init__(self, context: Context, logger: Logger | None = None):
        self._context = context
        self._logger = logger or getLogger(__name__)

    @property
    def context(self) -> Context:
        return self._context

    @property
    def logger(self) -> Logger:
        return self._logger


def async_use_case(
    return_response: BaseServiceResponse | None = None,
) -> Callable[[Callable[..., Awaitable]], Callable[..., Awaitable[BaseServiceResponse]]]:
    def decorator(func: Callable) -> Callable[..., Awaitable[BaseServiceResponse]]:
        async def wrapper(*args: Any, **kwargs: Any) -> BaseServiceResponse:
            base_response = return_response or BaseServiceResponse()
            try:
                return await func(*args, **kwargs)
            except BaseServiceError as e:
                base_response.set_unsuccessful_from_error(e)
            return base_response

        return wrapper

    return decorator
