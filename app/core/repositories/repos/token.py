from uuid import UUID

from app.core.enums import Tables
from app.schemas.dto import (
    UserTokenCreateSchema,
    UserTokenDto,
)

from .base import BaseRepository


class UserTokenRepo(BaseRepository):
    table = Tables.user_tokens

    async def get_by_user_id(self, user_id: UUID) -> UserTokenDto | None:
        query = f"""
        SELECT * 
        FROM {self.table} 
        WHERE user_id = :user_id
        """
        result = await self.db_client.execute_stmt(
            query, external_session=self._session, params={"user_id": user_id}, only_one=True
        )
        return UserTokenDto.model_validate(result) if result else None

    async def add(self, data: UserTokenCreateSchema) -> UserTokenDto:
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
        return UserTokenDto.model_validate(result)
