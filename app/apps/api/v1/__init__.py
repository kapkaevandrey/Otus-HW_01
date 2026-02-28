import logging

from fastapi import APIRouter

from app.apps.api.v1.login import auth_router
from app.apps.api.v1.user import users_router


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1")


router.include_router(users_router)
router.include_router(auth_router)
