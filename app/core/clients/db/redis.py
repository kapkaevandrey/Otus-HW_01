from collections.abc import Awaitable
from typing import Any, cast

from redis.asyncio import Redis
from redis.exceptions import ConnectionError, ResponseError

from app.config import REDIS_SCRIPTS_PATH, RedisSettings


class RedisClient(Redis):
    _scripts_sha_cache: dict[str, str]
    _lua_scripts: dict[str, str]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scripts_sha_cache = {}
        self._lua_scripts = {
            "send_message_to_user": (REDIS_SCRIPTS_PATH / "send_message_to_user.lua").read_text(encoding="utf-8"),
            "get_dialog_with_users": (REDIS_SCRIPTS_PATH / "get_dialog_with_users.lua").read_text(encoding="utf-8"),
        }

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

    async def send_message_to_user(
        self,
        *,
        direct_conversation_key: str,
        participants_key: str,
        messages_key: str,
        message_key: str,
        conversation_json_candidate: str,
        sender_id: str,
        receiver_id: str,
        message_member: str,
        message_json: str,
        sent_at_score: float,
    ) -> list[Any]:
        return await self._eval_dialog_script(
            name="send_message_to_user",
            keys=[direct_conversation_key, participants_key, messages_key, message_key],
            args=[
                conversation_json_candidate,
                sender_id,
                receiver_id,
                message_member,
                str(sent_at_score),
                message_json,
            ],
        )

    async def get_dialog_with_users(
        self,
        *,
        messages_key: str,
        message_key_prefix: str,
        offset: int = 0,
        limit: int = 1000,
        order: str = "desc",
    ) -> list[Any]:
        return await self._eval_dialog_script(
            name="get_dialog_with_users",
            keys=[messages_key, message_key_prefix],
            args=[str(offset), str(limit), order],
        )

    async def _eval_dialog_script(self, *, name: str, keys: list[str], args: list[str]) -> list[Any]:
        sha = self._scripts_sha_cache.get(name)
        if sha:
            try:
                result = self.evalsha(sha, len(keys), *keys, *args)
                if hasattr(result, "__await__"):
                    return cast(list[Any], await cast(Awaitable[Any], result))
                return cast(list[Any], result)
            except ResponseError as exc:
                if "NOSCRIPT" not in str(exc):
                    raise

        script = self._lua_scripts[name]
        loaded_sha = await self.script_load(script)
        if isinstance(loaded_sha, bytes):
            loaded_sha = loaded_sha.decode("utf-8")
        self._scripts_sha_cache[name] = loaded_sha
        result = self.evalsha(loaded_sha, len(keys), *keys, *args)
        if hasattr(result, "__await__"):
            return cast(list[Any], await cast(Awaitable[Any], result))
        return cast(list[Any], result)
