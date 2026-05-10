from fastapi import APIRouter

from .posts import feed_ws_router


ws_router = APIRouter()
ws_router.include_router(feed_ws_router)


__all__ = ["ws_router"]
