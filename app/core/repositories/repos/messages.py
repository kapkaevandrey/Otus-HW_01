from app.schemas.dto import MessageCreateSchema, MessageDto, MessageUpdateSchema

from .base import BaseRepository


class MessageRepo(BaseRepository[MessageDto, MessageCreateSchema, MessageUpdateSchema]):
    pass
