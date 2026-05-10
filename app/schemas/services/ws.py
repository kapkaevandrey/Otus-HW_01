import asyncio

from app.schemas.base import EmptyBaseSchema


class AsyncChannelQueue(EmptyBaseSchema):
    is_active: bool = True
    queue: asyncio.Queue


class InboxWsMessage(EmptyBaseSchema):
    event_type: str
    send_to_user_id: str
    payload: dict
