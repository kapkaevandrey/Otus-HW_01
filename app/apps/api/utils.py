from fastapi import HTTPException

from app.schemas.services import BaseServiceResponse


def raise_http_exception_from_service_response(response: BaseServiceResponse, retry_after: int = 15) -> None:
    if response.is_success:
        return
    headers = {"Retry-After": retry_after} if response.status >= 500 else {}
    raise HTTPException(
        status_code=response.status,
        detail={
            "message": response.error_message,
            "details": response.error_details,
            "headers": headers,
        },
    )
