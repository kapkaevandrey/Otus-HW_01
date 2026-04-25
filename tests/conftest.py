import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import db_settings, redis_settings
from app.core.clients import RedisClient, SQLAlchemyAsyncPgClient
from app.core.containers.context import Context, get_context
from app.server import app


pytest_plugins = ["tests.fixtures.instances", "tests.fixtures.mock_objects"]


TEST_DB_NAME = "_test_db"
db_settings.DB_DATABASE = TEST_DB_NAME

async_test_engine = create_async_engine(
    db_settings.db_dsn_master,
    echo=db_settings.DB_ECHO,
    poolclass=NullPool,
)
TestSessionMaker = async_sessionmaker(async_test_engine, expire_on_commit=False, autoflush=True, class_=AsyncSession)


@pytest.fixture()
def db_client() -> SQLAlchemyAsyncPgClient:
    return SQLAlchemyAsyncPgClient.from_settings(db_settings)


@pytest.fixture
async def redis_client() -> AsyncGenerator[RedisClient, Any]:
    client = RedisClient.from_settings(redis_settings)
    await client.flushdb()
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest.fixture(scope="session", autouse=True)
async def init_test_db():
    """
    Создаёт тестовую базу данных и после сессии тестов, удаляет её.
    """
    engine = create_async_engine(db_settings.db_master_url, isolation_level="AUTOCOMMIT")
    async with engine.begin() as conn:
        result = await conn.execute(text(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{TEST_DB_NAME}'"))
        if not result.scalar():
            await conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_settings.db_dsn_master.render_as_string(hide_password=False))
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: command.upgrade(alembic_cfg, "head"))
    yield
    async with engine.connect() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH(FORCE)"))


@pytest.fixture(scope="module")
async def reset_db():
    """
    Прогоняем все миграции на тестовую базу, чтобы была чистая структура.
    """
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_settings.db_dsn_master.render_as_string(hide_password=False))
    command.downgrade(alembic_cfg, "base")


@pytest.fixture(scope="function", autouse=True)
async def create_tables(request):
    """
    Создание таблиц (если они не созданы) и их очистка для каждого теста
    """
    if "disable_autouse" in request.keywords:
        yield
    else:
        engine = create_async_engine(db_settings.db_dsn_master, isolation_level="AUTOCOMMIT")
        yield
        async with engine.begin() as connection:
            result = await connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
            tables = [row[0] for row in result.fetchall()]
            if tables:
                tables_list = ", ".join(f'"{t}"' for t in tables)
                await connection.execute(text(f"TRUNCATE TABLE {tables_list} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def async_session_maker() -> async_sessionmaker[AsyncSession]:
    return TestSessionMaker


@pytest.fixture()
async def context(db_client: SQLAlchemyAsyncPgClient, kafka_producer_mock_client, redis_client) -> Context:
    context = Context(
        db_client=db_client,
        kafka_producer=kafka_producer_mock_client,
        redis_client=redis_client,
    )

    return context


@pytest.fixture
async def client(context):
    def _get_context():
        return context

    app.dependency_overrides[get_context] = _get_context

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
