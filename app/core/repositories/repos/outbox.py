from app.schemas.dto import EventActionOutboxCreateSchema, EventActionOutboxDto, EventActionOutboxUpdateSchema

from .base import BaseRepository


class EventActionOutboxRepo(
    BaseRepository[EventActionOutboxDto, EventActionOutboxCreateSchema, EventActionOutboxUpdateSchema]
):
    pass
