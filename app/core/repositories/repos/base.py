import logging
from abc import ABC
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clients.db import SQLAlchemyAsyncDbBaseClient


DtoSchemaType = TypeVar("DtoSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)


class BaseRepository[DtoSchemaType: BaseModel, CreateSchemaType: BaseModel, UpdateSchemaType: BaseModel](ABC):
    DEFAULT_BATCH_SIZE = 1_000

    def __init__(
        self,
        db_client: SQLAlchemyAsyncDbBaseClient,
        dto_schema: type[DtoSchemaType],
        session: AsyncSession | None = None,
        logger: logging.Logger | None = None,
    ):
        self.db_client = db_client
        self.dto_schema = dto_schema
        self._session = session
        self._logger = logger or logging.getLogger(__name__)

    async def get(self, pk_data: dict[str, Any]) -> DtoSchemaType | None:
        """TODO -"""

    async def remove(self, pk_data: dict[str, Any]) -> DtoSchemaType:
        """TODO -"""

    async def add(self):
        """TODO -"""
        pass

    async def add_batch(self, objs: list[CreateSchemaType]) -> list[DtoSchemaType]:
        """TODO -"""
        pass

    async def update(self, pk_data: dict[str, Any], data: UpdateSchemaType) -> DtoSchemaType:
        pass

    async def remove_by_attributes(
        self, where_params: dict[str, Any] | None = None, need_result: bool = False
    ) -> list[DtoSchemaType] | None:
        """TODO"""

    async def is_exists(self, where_params: dict) -> bool:
        """TODO"""

    async def update_by_attributes(
        self,
        where_params: dict[str, Any] | None = None,
        values: dict | None = None,
        need_result: bool = False,
    ) -> list[DtoSchemaType] | None:
        """TODO"""
