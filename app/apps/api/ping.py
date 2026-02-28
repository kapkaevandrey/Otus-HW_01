import asyncio
import logging
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException

from app.config import app_settings
from app.core.containers import Context, get_context


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/healthz", include_in_schema=False)
async def readiness_probe(context: Context = Depends(get_context)) -> str:
    await asyncio.gather(context.db_client.check_connection())
    return "OK"


@router.get("/livez", include_in_schema=False)
async def liveness_probe():
    return "OK"


if app_settings.DEBUG:

    @router.get("/http_error", include_in_schema=False)
    async def generate_http_error():
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Internal Server Error")
