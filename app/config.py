from functools import cached_property
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


BASE_DIR = Path(__file__).resolve().parent


class EmptyBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="allow", env_file=".env")


class AppSettings(EmptyBaseSettings):
    SERVICE_NAME: str = "otus-social"
    ROOT_PATH: str = ""
    SERVICE_DESCRIPTION: str = "Otus Homework for social network"
    STAND: str = "dev"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ALLOW_ORIGINS: str | None = None
    ENABLE_JSON_LOG: bool = True

    @property
    def allow_origins_list(self) -> list[str]:
        return self.ALLOW_ORIGINS.split(",") if self.ALLOW_ORIGINS else []


class AuthSettings(EmptyBaseSettings):
    JWT_PUB_KEY: str = "secret"
    JWT_PRIVATE_KEY: str = "secret"
    JWT_ALG: Literal["HS256", "RS256", "ES256"] = "HS256"
    JWT_ACCESS_EXP_SECONDS: int = 60 * 60
    JWT_REFRESH_EXP_SECONDS: int = 7 * 24 * 60 * 60
    AUTH_TOKEN_TYPE: str = "Bearer"


class DbSettings(EmptyBaseSettings):
    DB_MASTER_HOST: str = "db"
    DB_MASTER_PORT: int = 5432
    DB_MASTER_USER: str = "postgres"
    DB_MASTER_PASSWORD: str = "app_pswd"
    DB_DATABASE: str = "app_db"
    DB_ECHO: bool = False
    DB_DRIVER: str = "postgresql+asyncpg"
    DB_ENABLE_PG_BOUNCER: bool = False

    DB_REPLICAS: str = ""  # format host:port,host1:port1

    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 5
    DB_TIMEOUT: float = 30.0
    DB_POOL_RECYCLE: int = 3600

    @property
    def db_dsn_master(self) -> URL:
        return URL.create(
            self.DB_DRIVER,
            self.DB_MASTER_USER,
            self.DB_MASTER_PASSWORD,
            self.DB_MASTER_HOST,
            self.DB_MASTER_PORT,
            self.DB_DATABASE,
        )

    @property
    def db_master_url(self) -> URL:
        return URL.create(
            self.DB_DRIVER, self.DB_MASTER_USER, self.DB_MASTER_PASSWORD, self.DB_MASTER_HOST, self.DB_MASTER_PORT
        )

    @cached_property
    def db_replicas_dsns(self) -> list[URL]:
        result: list[URL] = []
        if not self.DB_REPLICAS:
            return result
        for string in self.DB_REPLICAS.split(","):
            host, port = string.split(":")
            result.append(
                URL.create(
                    self.DB_DRIVER, self.DB_MASTER_USER, self.DB_MASTER_PASSWORD, host, int(port), self.DB_DATABASE
                )
            )
        return result


app_settings = AppSettings()
auth_settings = AuthSettings()
db_settings = DbSettings()
