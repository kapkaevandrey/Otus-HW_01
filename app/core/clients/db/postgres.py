from typing import Any
from uuid import uuid4

from sqlalchemy import URL, AsyncAdaptedQueuePool, NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import DbSettings
from app.core.clients.db.base import SQLAlchemyAsyncDbBaseClient


class SQLAlchemyAsyncPgClient(SQLAlchemyAsyncDbBaseClient):
    def __init__(self, pg_bouncer_enabled: bool, *args: Any, **kwargs: Any):
        self._pg_bouncer_enabled: bool = pg_bouncer_enabled
        super().__init__(*args, **kwargs)

    @classmethod
    def from_settings(cls, settings: DbSettings) -> SQLAlchemyAsyncPgClient:
        connect_args = {}
        if settings.DB_ENABLE_PG_BOUNCER:
            connect_args["statement_cache_size"] = 0
            connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid4()}__"  # type: ignore
        return cls(
            host=settings.DB_MASTER_HOST,
            port=settings.DB_MASTER_PORT,
            username=settings.DB_MASTER_USER,
            password=settings.DB_MASTER_PASSWORD,
            database=settings.DB_DATABASE,
            db_driver=settings.DB_DRIVER,
            echo=settings.DB_ECHO,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pg_bouncer_enabled=settings.DB_ENABLE_PG_BOUNCER,
            replicas_urls=settings.db_replicas_dsns,
            connect_args=connect_args,
        )

    @property
    def master_engine(self) -> AsyncEngine:
        if self._master_engine is None:
            kwargs = {}
            keys = ["echo", "pool_size", "max_overflow", "pool_timeout", "pool_recycle"]
            if self._pg_bouncer_enabled:
                keys = ["echo"]
            for key in keys:
                if key in self.additional_params:
                    kwargs[key] = self.additional_params[key]
            self._master_engine = create_async_engine(
                self.db_master_url,
                **kwargs,
                future=True,
                poolclass=NullPool if self._pg_bouncer_enabled else AsyncAdaptedQueuePool,
                connect_args=self._connect_args,
            )
        return self._master_engine

    @property
    def replica_engines(self):
        if not self._replica_engines and self._replicas_urls:
            res = []
            kwargs = {}
            keys = ["echo", "pool_size", "max_overflow", "pool_timeout", "pool_recycle"]
            if self._pg_bouncer_enabled:
                keys = ["echo"]
            for key in keys:
                if key in self.additional_params:
                    kwargs[key] = self.additional_params[key]
            for url in self._replicas_urls:
                res.append(
                    create_async_engine(
                        url,
                        **kwargs,
                        future=True,
                        poolclass=NullPool if self._pg_bouncer_enabled else AsyncAdaptedQueuePool,
                        connect_args=self._connect_args,
                    )
                )
            self._replica_engines = res
        return self._replica_engines or []

    @property
    def db_master_url(self) -> URL:
        return URL.create(
            self._db_driver,
            self._user,
            self._password,
            self._host,
            self._port,
            self._database,
        )

    async def is_master(self, engine: AsyncEngine) -> bool:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT pg_is_in_recovery()"))
            return res.scalar() is False

    async def check_connection(self) -> None:
        query = "select 1 as param"
        await self.execute_stmt(query)
