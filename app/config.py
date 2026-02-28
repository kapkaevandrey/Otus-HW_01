from typing import Literal
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent


class EmptyBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="allow", env_file=".env")


class AppSettings(EmptyBaseSettings):
    SERVICE_NAME: str = "otus-social"
    SERVICE_DESCRIPTION: str = "Otus Homework for social network"
    STAND: str = "dev"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENABLE_JSON_LOG: bool = True


class AuthSettings(EmptyBaseSettings):
    JWT_PUB_KEY: str
    JWT_PRIVATE_KEY: str
    JWT_ALG: Literal["HS256", "RS256", "ES256"] = "HS256"
    JWT_ACCESS_EXP_SECONDS: int = 60 * 60
    JWT_REFRESH_EXP_SECONDS: int = 7 * 24 * 60 * 60


class DbSettings(EmptyBaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_DATABASE: str
    PG_BOUNCER_ENABLED: bool = False

    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 5
    DB_TIMEOUT: float = 30.0
    DB_POOL_RECYCLE: int = 3600


app_settings = AppSettings()
auth_settings = AuthSettings()
db_settings = DbSettings()
