from app.schemas.dto import UserOutboxCreateSchema, UserOutboxDto, UserOutboxUpdateSchema

from .base import BaseRepository


class UsersOutboxRepo(BaseRepository[UserOutboxDto, UserOutboxCreateSchema, UserOutboxUpdateSchema]):
    pass
