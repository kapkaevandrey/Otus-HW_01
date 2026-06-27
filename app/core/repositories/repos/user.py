from typing import Any

from app.core.enums import OutboxAction, Tables
from app.schemas.dto import (
    UserCreateSchema,
    UserDto,
    UserFriendCreateSchema,
    UserFriendDto,
    UserFriendUpdateSchema,
    UserOutboxDataSchema,
    UserUpdateSchema,
)

from .base import BaseRepository


class UserRepo(BaseRepository[UserDto, UserCreateSchema, UserUpdateSchema]):
    def __init__(self, *args: Any, **kwargs: Any):
        kwargs.setdefault("outbox_table", Tables.users_outbox)
        super().__init__(*args, **kwargs)

    async def prepare_outbox_data(self, dto: UserDto) -> dict[str, Any]:
        return UserOutboxDataSchema(
            id=dto.id,
            first_name=dto.first_name,
            second_name=dto.second_name,
            birthdate=dto.birthdate,
            biography=dto.biography,
            city=dto.city,
        ).model_dump(mode="json")

    async def add(self, data: UserCreateSchema) -> UserDto:
        dto = await super().add(data)
        await self.save_outbox(OutboxAction.CREATE, await self.prepare_outbox_data(dto))
        return dto

    async def update(self, pk_data: dict[str, Any], data: UserUpdateSchema, exclude_none: bool = False) -> UserDto:
        dto = await super().update(pk_data, data, exclude_none=exclude_none)
        await self.save_outbox(OutboxAction.UPDATE, await self.prepare_outbox_data(dto))
        return dto

    async def remove(self, pk_data: dict[str, Any]) -> UserDto:
        dto = await super().remove(pk_data)
        await self.save_outbox(OutboxAction.DELETE, await self.prepare_outbox_data(dto))
        return dto


class UserFriendsRepo(BaseRepository[UserFriendDto, UserFriendCreateSchema, UserFriendUpdateSchema]):
    pass
