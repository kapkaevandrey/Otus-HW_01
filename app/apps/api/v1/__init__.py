import logging

from fastapi import APIRouter

from .friend import friends_router
from .login import auth_router
from .posts import posts_router
from .user import users_router


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1")


router.include_router(users_router)
router.include_router(auth_router)
router.include_router(friends_router)
router.include_router(posts_router)
