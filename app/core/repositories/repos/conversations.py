from app.schemas.dto import (
    ConversationCreateSchema,
    ConversationDto,
    ConversationParticipantsCreateSchema,
    ConversationParticipantsDto,
    ConversationParticipantsUpdateSchema,
    ConversationUpdateSchema,
)

from .base import BaseRepository


class ConversationRepo(BaseRepository[ConversationDto, ConversationCreateSchema, ConversationUpdateSchema]):
    pass


class ConversationParticipantsRepo(
    BaseRepository[
        ConversationParticipantsDto, ConversationParticipantsCreateSchema, ConversationParticipantsUpdateSchema
    ]
):
    pass
