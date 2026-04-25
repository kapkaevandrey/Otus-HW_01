from redis.asyncio import Redis
from redis.exceptions import ConnectionError

from app.config import RedisSettings


class RedisClient(Redis):
    @classmethod
    def from_settings(cls, settings: RedisSettings) -> RedisClient:
        return cls(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            max_connections=settings.REDIS_POOL_MAX_SIZE,
            retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
            retry_on_error=[ConnectionError],
            health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
            ssl=settings.REDIS_SSL,
            socket_connect_timeout=settings.REDIS_TIMEOUT_SEC,
            socket_timeout=settings.REDIS_TIMEOUT_SEC,
        )
