import asyncio

from app.schemas.base import EmptyBaseSchema


class AsyncChannelQueue(EmptyBaseSchema):
    is_active: bool = True
    queue: asyncio.Queue
