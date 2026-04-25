from app.schemas.base import EmptyBaseSchema


class ServiceEvent(EmptyBaseSchema):
    event_type: str
    data: dict
