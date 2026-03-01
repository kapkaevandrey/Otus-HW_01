import asyncio
from abc import ABC, abstractmethod
from collections.abc import Sequence
from logging import Logger, getLogger
from typing import Any

from sqlalchemy import Executable, Result, Row, RowMapping, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.exceptions import DatabaseError


class SQLAlchemyAsyncDbBaseClient(ABC):
    DB_ERROR_MESSAGE = "Error when executing a database query: {exc}"

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        database: str,
        db_driver: str,
        connect_args: dict | None = None,
        logger: Logger | None = None,
        **kwargs: Any,
    ):
        self.logger = logger or getLogger(__name__)
        self._host = host
        self._port = port
        self._user = username
        self._password = password
        self._database = database
        self._db_driver = db_driver
        self.additional_params = kwargs
        self._engine: AsyncEngine | None = None
        self._connect_args = connect_args or {}
        self._session_maker: async_sessionmaker[AsyncSession] | None = None

    @classmethod
    def from_settings(cls, settings: Any) -> SQLAlchemyAsyncDbBaseClient:
        raise NotImplementedError

    @property
    def session_maker(self) -> async_sessionmaker[AsyncSession]:
        raise NotImplementedError

    @property
    def engine(self) -> AsyncEngine:
        raise NotImplementedError

    @abstractmethod
    async def check_connection(self) -> None:
        raise NotImplementedError

    async def execute_stmt(
        self,
        query: str,
        params: list[dict] | dict | None = None,
        external_session: AsyncSession | None = None,
        commit: bool = True,
        mapped: bool = True,
        only_one: bool = True,
        need_result: bool = True,
        tries: int = 3,
        delay: float = 0.2,
    ) -> Any:
        stmt = text(query)
        _session = external_session or self.session_maker()
        try:
            proxy_result = await self._try_execute_stmt(
                stmt=stmt, params=params, session=_session, tries=tries, delay=delay
            )
            if need_result:
                return self._collect_result_from_proxy(proxy_result, mapped, only_one)
        except DatabaseError:
            if not external_session:
                await _session.rollback()
            raise
        finally:
            if not external_session and commit:
                await _session.commit()
            if not external_session:
                await _session.close()

    async def _try_execute_stmt(
        self, stmt: Executable, params: dict | list[dict] | None, session: AsyncSession, tries: int, delay: float
    ) -> Result:
        exception = None
        for trie in range(tries):
            try:
                return await session.execute(stmt, params)
            except Exception as exc:
                if trie == tries - 1:
                    exception = exc
                    self.logger.error(self.DB_ERROR_MESSAGE.format(exc=exception), exc_info=True)
                    break
                await session.rollback()
            await asyncio.sleep(delay)
        raise DatabaseError(self.DB_ERROR_MESSAGE.format(exc=exception)) from exception

    @staticmethod
    def _collect_result_from_proxy(proxy_result: Result, mapped: bool, only_one: bool) -> Any:
        result: RowMapping | Row | Sequence[RowMapping] | Sequence[Row] | None = None
        match (mapped, only_one):
            case (True, True):
                result = proxy_result.mappings().fetchone()
            case (True, False):
                result = proxy_result.mappings().fetchall()
            case (_, True):
                result = proxy_result.fetchone()
            case (_, False):
                result = proxy_result.fetchall()

        return result
