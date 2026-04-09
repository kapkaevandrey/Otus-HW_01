import asyncio
import random as rnd
from abc import ABC, abstractmethod
from enum import StrEnum
from logging import Logger, getLogger
from typing import Any

from sqlalchemy import URL, Executable, Result, text
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.exceptions import ConnectionDbError, DatabaseError


class SessionOperations(StrEnum):
    READ = "read"
    READ_WRITE = "read_write"


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
        replicas_urls: list[URL] | None = None,
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
        self._connect_args = connect_args or {}
        self._replicas_urls = replicas_urls or []
        self._master_engine: AsyncEngine | None = None
        self._replica_engines: list[AsyncEngine] | None = None
        self._engines_lives_map: dict[AsyncEngine, bool] = {
            self.master_engine: True,
            **dict.fromkeys(self.replica_engines or [], True),
        }
        self._session_maker_maps: dict[AsyncEngine, async_sessionmaker[AsyncSession]] = {}
        self._all_engines = [self.master_engine, *self.replica_engines]
        self._engine_map = {
            SessionOperations.READ: list(self.replica_engines),
            SessionOperations.READ_WRITE: [self.master_engine],
        }
        self._need_check_dead_connections: set[AsyncEngine] = set()
        self._check_dead_connection_task: asyncio.Task | None = None

    async def start_client(self) -> None:
        await self.refresh_read_write_consistency()
        self._check_dead_connection_task = asyncio.create_task(self.check_dead_connection_task())

    async def stop_client(self) -> None:
        if self._check_dead_connection_task:
            self._check_dead_connection_task.cancel()

    async def check_dead_connection_task(self) -> None:
        while True:
            for eng in self._need_check_dead_connections:
                try:
                    await self.check_connection(eng)
                    self._need_check_dead_connections.remove(eng)
                    self._engines_lives_map[eng] = True
                except Exception:
                    self.logger.error("Connection is dead", exc_info=True)
            await asyncio.sleep(10)

    @classmethod
    def from_settings(cls, settings: Any) -> SQLAlchemyAsyncDbBaseClient:
        raise NotImplementedError

    @property
    def master_engine(self) -> AsyncEngine:
        raise NotImplementedError

    @property
    def replica_engines(self) -> list[AsyncEngine]:
        raise NotImplementedError

    @abstractmethod
    async def check_connection(self, engine: AsyncEngine) -> None:
        raise NotImplementedError

    @abstractmethod
    async def is_master(self, engine: AsyncEngine) -> bool:
        pass

    def _get_alive_engines(self, op: SessionOperations) -> list[AsyncEngine]:
        engines = self._engine_map.get(op, [])
        return [e for e in engines if self._engines_lives_map.get(e, True)]

    def _choose_engine(self, read_only: bool) -> AsyncEngine:
        masters = self._get_alive_engines(SessionOperations.READ_WRITE)
        replicas = self._get_alive_engines(SessionOperations.READ)
        pool = (replicas or masters) if read_only else masters
        if not pool:
            raise DatabaseError("No alive DB engines")
        return rnd.choice(pool)

    def get_session_maker(self, read_only: bool = False) -> async_sessionmaker[AsyncSession]:
        engine = self._choose_engine(read_only)
        if engine not in self._session_maker_maps:
            self._session_maker_maps[engine] = async_sessionmaker(
                engine,
                expire_on_commit=False,
                autoflush=False,
            )
        return self._session_maker_maps[engine]

    async def refresh_read_write_consistency(self) -> None:
        new_map: dict[SessionOperations, list[AsyncEngine]] = {
            SessionOperations.READ: [],
            SessionOperations.READ_WRITE: [],
        }
        results = await asyncio.gather(
            *(self.is_master(engine) for engine in self._all_engines), return_exceptions=True
        )
        for res, eng in zip(results, self._all_engines, strict=False):
            if isinstance(res, Exception):
                self._engines_lives_map[eng] = False
                self._need_check_dead_connections.add(eng)
            else:
                self._engines_lives_map[eng] = True
            if res:
                new_map[SessionOperations.READ_WRITE].append(eng)
            else:
                new_map[SessionOperations.READ].append(eng)
        self._engine_map = new_map

    @staticmethod
    def is_retryable_error(exc: Exception) -> bool:
        if isinstance(exc, (OperationalError, InterfaceError)):
            return True
        if isinstance(exc, DBAPIError):
            return exc.connection_invalidated
        return False

    async def execute_stmt(
        self,
        query: str,
        params: dict | None = None,
        external_session: AsyncSession | None = None,
        commit: bool = True,
        mapped: bool = True,
        only_one: bool = False,
        need_result: bool = True,
        tries: int = 3,
        delay: float = 0.2,
    ) -> Any:
        stmt = text(query)
        session_maker = self.get_session_maker()
        _session = external_session or session_maker()
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
                if not self.is_retryable_error(exc):
                    raise ConnectionDbError from exc
                if trie == tries - 1:
                    exception = exc
                    self.logger.error(self.DB_ERROR_MESSAGE.format(exc=exception), exc_info=True)
                    break
                await session.rollback()
            await asyncio.sleep(delay)
        raise DatabaseError(self.DB_ERROR_MESSAGE.format(exc=exception)) from exception

    @staticmethod
    def _collect_result_from_proxy(
        proxy_result: Result, mapped: bool, only_one: bool
    ) -> list[tuple] | list[dict] | dict | tuple | None:
        result: list[tuple] | list[dict] | dict | tuple | None = None
        match (mapped, only_one):
            case (True, True):
                row = proxy_result.mappings().fetchone()
                result = dict(row) if row else None
            case (True, False):
                rows = proxy_result.mappings().fetchall()
                result = [dict(r) for r in rows] if rows else []
            case (_, True):
                row = proxy_result.fetchone()  # type: ignore
                result = tuple(row) if row else None
            case (_, False):
                row = proxy_result.fetchall()  # type: ignore
                result = [tuple(r) for r in row] if row else []
        return result
