import os
from typing import Any
from uuid import uuid4

from sqlalchemy import URL, AsyncAdaptedQueuePool, NullPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import DbSettings
from app.core.clients.db.base import SQLAlchemyAsyncDbBaseClient


class SQLAlchemyAsyncPgClient(SQLAlchemyAsyncDbBaseClient):
    def __init__(self, pg_bouncer_enabled: bool, *args: Any, **kwargs: Any):
        self._pg_bouncer_enabled: bool = pg_bouncer_enabled
        super().__init__(*args, **kwargs)

    @classmethod
    def from_settings(cls, settings: DbSettings) -> "SQLAlchemyAsyncPgClient":
        connect_args = {"server_settings": {"application_name": os.uname().nodename}}
        if settings.DB_ENABLE_PG_BOUNCER:
            connect_args["statement_cache_size"] = 0  # type: ignore
            connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid4()}__"  # type: ignore
        return cls(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            username=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_DATABASE,
            db_driver=settings.DB_DRIVER,
            echo=settings.DB_ECHO,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pg_bouncer_enabled=settings.DB_ENABLE_PG_BOUNCER,
            connect_args=connect_args,
        )

    @property
    def session_maker(self) -> async_sessionmaker[AsyncSession]:
        if not self._session_maker:
            self._session_maker = async_sessionmaker(
                self.engine,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
        return self._session_maker

    @property
    def engine(self) -> AsyncEngine:
        if not self._engine:
            kwargs = {}
            keys = ["echo", "pool_size", "max_overflow", "pool_timeout", "pool_recycle"]
            if self._pg_bouncer_enabled:
                keys = ["echo"]
            for key in keys:
                if key in self.additional_params:
                    kwargs[key] = self.additional_params[key]
            self._engine = create_async_engine(
                self.db_url,
                **kwargs,
                future=True,
                poolclass=NullPool if self._pg_bouncer_enabled else AsyncAdaptedQueuePool,
                connect_args=self._connect_args,
            )
        return self._engine

    @property
    def db_url(self) -> URL:
        return URL.create(
            self._db_driver,
            self._user,
            self._password,
            self._host,
            self._port,
            self._database,
        )

    async def check_connection(self) -> None:
        query = "select 1 as param"
        await self.execute_stmt(query)
