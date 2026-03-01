import logging
from abc import ABC

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clients.db import SQLAlchemyAsyncDbBaseClient


class BaseRepository(ABC):
    table: str

    def __init__(
        self,
        db_client: SQLAlchemyAsyncDbBaseClient,
        session: AsyncSession | None = None,
        logger: logging.Logger | None = None,
    ):
        self.db_client = db_client
        self._session = session
        self._logger = logger or logging.getLogger(__name__)
