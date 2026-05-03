from app.schemas.base import EmptyBaseSchema


class SendMessageSchema(EmptyBaseSchema):
    text: str
