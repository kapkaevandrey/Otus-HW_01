from __future__ import annotations

from typing import Any

from app.schemas.base import EmptyBaseSchema


class HttpClientRequest(EmptyBaseSchema):
    url: str
    method: str
    payload: Any | None = None
    query: dict[str, Any] | None = None
    headers: dict[str, str] | None = None


class HttpClientResponse(EmptyBaseSchema):
    request: HttpClientRequest
    status: int
    is_success: bool
    is_json: bool
    json_data: Any | None = None
    text: str | None = None
    headers: dict[str, str]
    elapsed_sec: float | None = None
    reason_phrase: str | None = None
    content_length: int | None = None
