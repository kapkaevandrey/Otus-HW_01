from uuid import UUID

from app.core.enums import ConversationTypes
from app.schemas.base import EmptyBaseSchema
from app.schemas.types import NotEmptyString


class SendMessageServiceSchema(EmptyBaseSchema):
    text: NotEmptyString
    user_sender: UUID
    user_receiver: UUID


class SendMessageServiceResponse(EmptyBaseSchema):
    message_id: UUID
    conversation_id: UUID
    sender_id: UUID
    conversation_type: ConversationTypes
