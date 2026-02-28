from http import HTTPStatus
from typing import Any, TypeVar

from app.exceptions import BaseServiceError
from app.schemas.base import EmptyBaseSchema


ResultType = TypeVar("ResultType")


class BaseServiceResponse[ResultType](EmptyBaseSchema):
    status: HTTPStatus | int = HTTPStatus.OK
    is_success: bool = True
    result: ResultType | Any = None
    error_message: str | None = None
    error_details: dict = {}

    def set_unsuccessful(
        self,
        status: HTTPStatus | int = HTTPStatus.BAD_REQUEST,
        error_message: str | None = None,
        error_detail: dict | None = None,
    ) -> None:
        self.status = status
        self.is_success = False
        self.error_message = error_message or self.error_message
        for key, value in (error_detail or {}).items():
            if key not in self.error_details:
                self.error_details[key] = []
            if isinstance(value, (list, set, tuple)):
                self.error_details[key].extend(list(value))
            else:
                self.error_details[key].append(value)

    def set_unsuccessful_from_error(self, error: BaseServiceError) -> None:
        if not isinstance(error, BaseServiceError):
            raise TypeError("Error must be a BaseServiceError instance")
        self.set_unsuccessful(status=error.status, error_message=error.error_message, error_detail=error.error_details)
