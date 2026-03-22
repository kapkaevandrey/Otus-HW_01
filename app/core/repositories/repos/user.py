from uuid import UUID

from app.core.enums import Tables
from app.schemas.dto import (
    UserCreateSchema,
    UserDto,
)

from .base import BaseRepository


class UserRepo(BaseRepository):
    table = Tables.users
    MAX_ARGS = 30_000

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

    async def add_batch(self, data: list[UserCreateSchema]) -> list[UserDto]:
        if not data:
            raise ValueError("No values provided for insert")
        keys = UserCreateSchema.model_fields.keys()
        columns = ", ".join(keys)
        batch_size = self.MAX_ARGS // len(keys)
        all_results = []
        for i in range(0, len(data), batch_size):
            insert_data = [el.model_dump() for el in data[i : i + batch_size]]
            values_placeholders = [", ".join(f":{key}{ind}" for key in keys) for ind in range(len(insert_data))]
            values = {f"{key}{ind}": el[key] for key in keys for ind, el in enumerate(insert_data)}
            val_places = ", ".join([f"({el})" for el in values_placeholders])
            query = f"""
            INSERT INTO {self.table} ({columns})
            VALUES {val_places}
            RETURNING *
            """
            result = await self.db_client.execute_stmt(query, params=values, external_session=self._session)
            all_results.extend(result)
        return [UserDto.model_validate(result) for result in all_results]

    async def search_by_first_name_last_name(
        self, first_name: str, second_name: str, ilike: bool = False
    ) -> list[UserDto]:
        first_name = first_name if first_name.endswith("%") else f"{first_name}%"
        second_name = second_name if second_name.endswith("%") else f"{second_name}%"
        method = "ILIKE" if ilike else "LIKE"
        query = f"""
        SELECT * 
        FROM {self.table} 
        WHERE first_name {method} :first_name AND second_name {method} :second_name 
        """
        result = await self.db_client.execute_stmt(
            query, external_session=self._session, params={"first_name": first_name, "second_name": second_name}
        )
        return [UserDto.model_validate(el) for el in result] if result else []
