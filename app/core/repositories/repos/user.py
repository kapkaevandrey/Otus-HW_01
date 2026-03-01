from uuid import UUID

from app.core.enums import Tables
from app.schemas.dto import (
    UserCreateSchema,
    UserDto,
)

from .base import BaseRepository


class UserRepo(BaseRepository):
    table = Tables.users

    async def get(self, user_id: UUID) -> UserDto | None:
        query = f"""
        SELECT * 
        FROM {self.table} 
        WHERE id = :id
        """
        result = await self.db_client.execute_stmt(
            query, external_session=self._session, params={"id": user_id}, only_one=True
        )
        return UserDto.model_validate(result) if result else None

    async def add(self, data: UserCreateSchema) -> UserDto:
        insert_values = data.model_dump()
        if not insert_values:
            raise ValueError("No values provided for insert")
        columns = ", ".join(insert_values.keys())
        values_placeholders = ", ".join(f":{key}" for key in insert_values)
        query = f"""
            INSERT INTO {self.table} ({columns})
            VALUES ({values_placeholders})
            RETURNING *
        """
        result = await self.db_client.execute_stmt(
            query, params=insert_values, external_session=self._session, only_one=True
        )
        return UserDto.model_validate(result)
