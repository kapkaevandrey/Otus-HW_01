from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

import httpx

from app.exceptions import BaseClientError

from .schemas import HttpClientRequest, HttpClientResponse


logger = logging.getLogger(__name__)


class BaseHttpClient:
    CLIENT_NAME = "base_http"

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        *,
        raise_on_error: bool = True,
        default_headers: dict[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._raise_on_error = raise_on_error
        self._default_headers = default_headers or {}
        self._client = client
        self._owned_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        if self._owned_client is None:
            self._owned_client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)
        return self._owned_client

    async def aclose(self) -> None:
        if self._owned_client is not None:
            await self._owned_client.aclose()
            self._owned_client = None

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> HttpClientResponse:
        merged_headers = {**self._default_headers, **(headers or {})}
        request_meta = HttpClientRequest(
            url=self._build_request_url(url),
            method=method.upper(),
            payload=json,
            query=params,
            headers=merged_headers or None,
        )
        try:
            httpx_response = await (await self._get_client()).request(
                method,
                url,
                params=params,
                json=json,
                headers=merged_headers or None,
                **kwargs,
            )
        except httpx.RequestError as exc:
            raise BaseClientError(
                error_message=str(exc),
                client_name=self.CLIENT_NAME,
                status=HTTPStatus.BAD_GATEWAY,
                error_details={
                    "url": request_meta.url,
                    "method": request_meta.method,
                },
            ) from exc

        response = self._build_response(httpx_response, request_meta)
        if self._raise_on_error and not response.is_success:
            raise self._error_from_response(response)
        return response

    def _build_request_url(self, url: str) -> str:
        if url.startswith(("http://", "https://")):
            return url
        return f"{self._base_url}/{url.lstrip('/')}"

    @classmethod
    def _build_response(cls, httpx_response: httpx.Response, request_meta: HttpClientRequest) -> HttpClientResponse:
        content_type = httpx_response.headers.get("content-type", "")
        is_json = "application/json" in content_type.lower()
        json_data: Any | None = None
        text: str | None = None

        if is_json:
            try:
                json_data = httpx_response.json()
            except ValueError:
                is_json = False
                text = httpx_response.text
        else:
            text = httpx_response.text

        actual_request = httpx_response.request
        request_meta = request_meta.model_copy(
            update={
                "url": str(actual_request.url),
                "method": actual_request.method,
                "headers": dict(actual_request.headers),
            }
        )

        status = httpx_response.status_code
        elapsed_sec = None
        if hasattr(httpx_response, "_elapsed"):
            elapsed_sec = httpx_response.elapsed.total_seconds()

        return HttpClientResponse(
            request=request_meta,
            status=status,
            is_success=httpx.codes.is_success(status),
            is_json=is_json,
            json_data=json_data,
            text=text,
            headers=dict(httpx_response.headers),
            elapsed_sec=elapsed_sec,
            reason_phrase=httpx_response.reason_phrase,
            content_length=len(httpx_response.content) if httpx_response.content is not None else None,
        )

    def _error_from_response(self, response: HttpClientResponse) -> BaseClientError:
        error_message, error_details = self._extract_error_payload(response)
        logger.warning(
            "HTTP client request failed",
            extra={
                "client_name": self.CLIENT_NAME,
                "status": response.status,
                "url": response.request.url,
                "method": response.request.method,
            },
        )
        return BaseClientError(
            error_message=error_message,
            client_name=self.CLIENT_NAME,
            status=response.status,
            error_details=error_details,
        )

    @staticmethod
    def _extract_error_payload(response: HttpClientResponse) -> tuple[str, dict[str, Any]]:
        default_message = response.reason_phrase or f"HTTP {response.status}"
        details: dict[str, Any] = {
            "url": response.request.url,
            "method": response.request.method,
        }

        if not response.is_json or not isinstance(response.json_data, dict):
            if response.text:
                details["body"] = response.text
            return default_message, details

        payload = response.json_data
        details["body"] = payload

        detail = payload.get("detail")
        if isinstance(detail, dict):
            message = detail.get("message") or default_message
            if detail.get("details") is not None:
                details["remote_details"] = detail["details"]
            return str(message), details
        if isinstance(detail, str):
            return detail, details
        if payload.get("message"):
            return str(payload["message"]), details

        return default_message, details
