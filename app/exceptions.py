import logging
from http import HTTPStatus


logger = logging.getLogger(__name__)


class BaseServiceError(Exception):
    def __init__(
        self,
        error_message: str | None,
        status: HTTPStatus | int = HTTPStatus.BAD_REQUEST,
        error_details: dict | None = None,
    ):
        """A basic exception from service layer.

        Args:
            error_message (str): Error message.
            status (HTTPStatus | int): HTTP status code.
            error_details (Optional[dict]): Error details.
        """
        self.error_details = error_details or {}
        self.error_message = error_message
        self.status = status
        super().__init__()


class DatabaseError(Exception):
    pass


class ConnectionDbError(DatabaseError):
    pass
