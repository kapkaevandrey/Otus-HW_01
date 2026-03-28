import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import Logger
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clients.db import SQLAlchemyAsyncDbBaseClient

from .repos import BaseRepository, UserRepo


class UnitOfWork:
    def __init__(self, db_client: SQLAlchemyAsyncDbBaseClient):
        self.db_client = db_client
        self._logger = logging.getLogger(__name__)
        self._session: AsyncSession | None = None
        self._user_repo = UserRepo(db_client)

    @property
    def repositories(self) -> list[BaseRepository]:
        return [
            self._user_repo,
        ]

    @property
    def user_repo(self) -> UserRepo:
        return self._user_repo

    @property
    def logger(self) -> Logger:
        return self._logger

    @asynccontextmanager
    async def transaction(self, transaction_context: dict | None = None) -> AsyncGenerator[UnitOfWork]:
        transaction_id = str(uuid4())
        transaction_context = transaction_context or {}
        transaction_context["transaction_id"] = transaction_id
        if self._session is None:
            async with self.db_client.session_maker() as session:
                self.logger.debug("Transaction: %s started", transaction_id)
                self._fill_repos_session(session)
                try:
                    yield self
                    await session.commit()
                    self.logger.debug("Transaction: %s commited", transaction_id)
                except Exception:
                    await session.rollback()
                    self.logger.debug("Transaction: %s aborted", transaction_id)
                    raise
                finally:
                    self._fill_repos_session()
                    self.logger.debug("Transaction: %s finished", transaction_id)
        else:
            savepoint = await self._session.begin_nested()
            try:
                yield self
                await savepoint.commit()
                self.logger.debug("Savepoint in nested transaction: rolled back")
            except Exception:
                await savepoint.rollback()
                self.logger.debug("Savepoint in nested transaction: rolled back")
                raise

    def _fill_repos_session(self, session: AsyncSession | None = None) -> None:
        self._session = session
        for repo in self.repositories:
            repo._session = session
