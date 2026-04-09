from logging import Logger, getLogger

from app.config import db_settings
from app.core.clients import SQLAlchemyAsyncPgClient
from app.core.repositories import UnitOfWork


logger = getLogger(__name__)


class Context:
    def __init__(
        self,
        db_client: SQLAlchemyAsyncPgClient,
        logger: Logger | None = None,
    ) -> None:
        self._db_client = db_client
        self._logger = logger or getLogger(__name__)

    @property
    def db_client(self) -> SQLAlchemyAsyncPgClient:
        return self._db_client

    @property
    def uow(self):
        return UnitOfWork(db_client=self._db_client)

    @property
    def logger(self) -> Logger:
        return self._logger

    async def start_clients(self):
        """Start all clients if that need"""
        await self.db_client.start_client()

    async def stop_clients(self):
        """Stop all clients if that need"""
        await self.db_client.stop_client()


context = Context(
    db_client=SQLAlchemyAsyncPgClient.from_settings(db_settings),
    logger=getLogger(__name__),
)


def get_context() -> Context:
    return context
