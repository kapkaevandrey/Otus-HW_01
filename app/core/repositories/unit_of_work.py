import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import Logger
from typing import Self
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clients.db import SQLAlchemyAsyncDbBaseClient
from app.core.enums import Tables
from app.schemas.dto import UserDto, UserFriendDto, UserPublicationDto

from .repos import BaseRepository, UserFriendsRepo, UserPublicationRepo, UserRepo


class UnitOfWork:
    def __init__(self, db_client: SQLAlchemyAsyncDbBaseClient):
        self.db_client = db_client
        self._logger = logging.getLogger(__name__)
        self._session: AsyncSession | None = None
        self._user_repo = UserRepo(db_client=db_client, table=Tables.users, dto_schema=UserDto)
        self._user_friends_repo = UserFriendsRepo(
            db_client=db_client, table=Tables.users_friends, dto_schema=UserFriendDto
        )
        self._user_publication_repo = UserPublicationRepo(
            db_client=db_client, table=Tables.users_publications, dto_schema=UserPublicationDto
        )

    @property
    def repositories(self) -> list[BaseRepository]:
        return [
            self._user_repo,
            self._user_friends_repo,
            self._user_publication_repo,
        ]

    @property
    def user_repo(self) -> UserRepo:
        return self._user_repo

    @property
    def user_friends_repo(self) -> UserFriendsRepo:
        return self._user_friends_repo

    @property
    def user_publication_repo(self) -> UserPublicationRepo:
        return self._user_publication_repo

    @property
    def logger(self) -> Logger:
        return self._logger

    @asynccontextmanager
    async def transaction(
        self, transaction_context: dict | None = None, read_only: bool = False
    ) -> AsyncGenerator[UnitOfWork]:
        transaction_id = str(uuid4())
        transaction_context = transaction_context or {}
        transaction_context["transaction_id"] = transaction_id
        if self._session is None:
            session_maker = self.db_client.get_session_maker(read_only=read_only)
            async with session_maker() as session:
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

    @asynccontextmanager
    async def _processing_session(self, session: AsyncSession, transaction_id: str) -> AsyncGenerator[Self]:
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
