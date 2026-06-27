from __future__ import annotations

from contextvars import ContextVar


REQUEST_ID_HEADER = "X-Request-Id"

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return request_id_ctx.get()
