from app.schemas.dto import (
    UserCreateSchema,
    UserDto,
    UserFriendCreateSchema,
    UserFriendDto,
    UserFriendUpdateSchema,
    UserUpdateSchema,
)

from .base import BaseRepository


class UserRepo(BaseRepository[UserDto, UserCreateSchema, UserUpdateSchema]):
    pass


class UserFriendsRepo(BaseRepository[UserFriendDto, UserFriendCreateSchema, UserFriendUpdateSchema]):
    pass
