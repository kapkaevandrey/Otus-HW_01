from logging import Logger, getLogger
from typing import TypeVar


DataType = TypeVar("DataType")


class ServiceUtils:
    DEFAULT_RETRIES = 3
    DEFAULT_RETRIE_DELAY = 0.2

    def __init__(self, logger: Logger | None = None):
        self.logger = logger or getLogger(__name__)
