import logging

from fastapi import APIRouter

from app.apps.api.ping import router as ping_router
from app.apps.api.v1 import router as v1_router


logger = logging.getLogger(__name__)
main_router = APIRouter()

main_router.include_router(v1_router, prefix="/api")
main_router.include_router(ping_router, include_in_schema=False)
