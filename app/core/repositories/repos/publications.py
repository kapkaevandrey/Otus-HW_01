from app.schemas.dto import UserPublicationCreateSchema, UserPublicationDto, UserPublicationUpdateSchema

from .base import BaseRepository


class UserPublicationRepo(BaseRepository[UserPublicationDto, UserPublicationCreateSchema, UserPublicationUpdateSchema]):
    pass
