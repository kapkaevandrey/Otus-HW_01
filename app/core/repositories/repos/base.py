import logging
from collections import defaultdict
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clients.db import SQLAlchemyAsyncDbBaseClient
from app.core.enums import StrEnum
from app.exceptions import DatabaseInstanceNotFoundError, DatabaseMultiplyResultError
from app.schemas.base import EmptyBaseSchema

from .schemas import JoinCondition, JoinType


DtoSchemaType = TypeVar("DtoSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)


class JoinParams(EmptyBaseSchema):
    orig_repo: BaseRepository
    joined_repo: BaseRepository
    join_type: JoinType = JoinType.INNER
    on: list[JoinCondition]
    where: dict[str, Any] | None = None
    order_by: list[str] | None = None


class LookupExpressionSuffixes(StrEnum):
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"
    EQ = "eq"
    NEQ = "neq"
    IS = "is"
    IS_NOT = "is_not"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"
    I_LIKE = "ilike"
    LIKE = "like"


class OrderTypes(StrEnum):
    ASCENDING = "asc"
    DESCENDING = "desc"


class BaseRepository[DtoSchemaType: BaseModel, CreateSchemaType: BaseModel, UpdateSchemaType: BaseModel]:
    __LOOKUP_EXPRESSION_DEFAULT_SEPARATOR = "__"
    EQUAL_DEFAULT_LOOKUP_SUFFIX = LookupExpressionSuffixes.EQ
    LOOKUP_EXPRESSION_OPERATOR_MAP: dict[str, str] = {
        LookupExpressionSuffixes.LT: "<",
        LookupExpressionSuffixes.LE: "<=",
        LookupExpressionSuffixes.GT: ">",
        LookupExpressionSuffixes.GE: ">=",
        LookupExpressionSuffixes.EQ: "=",
        LookupExpressionSuffixes.NEQ: "!=",
        LookupExpressionSuffixes.IS: "IS",
        LookupExpressionSuffixes.IS_NOT: "IS NOT",
        LookupExpressionSuffixes.I_LIKE: "ILIKE",
        LookupExpressionSuffixes.LIKE: "LIKE",
    }
    ORDER_PREFIX_MAP: dict[str, str] = {
        OrderTypes.ASCENDING: "",
        OrderTypes.DESCENDING: "DESC",
    }
    DEFAULT_ORDER_TYPE = OrderTypes.ASCENDING
    MAX_ARGS = 30_000

    def __init__(
        self,
        table: str,
        db_client: SQLAlchemyAsyncDbBaseClient,
        dto_schema: type[DtoSchemaType],
        session: AsyncSession | None = None,
        logger: logging.Logger | None = None,
    ):
        self.db_client = db_client
        self.dto_schema = dto_schema
        self._session = session
        self._table = table
        self._logger = logger or logging.getLogger(__name__)

    async def count(
        self,
        where_params: dict[str, Any] | None = None,
    ) -> int:
        _where_params = where_params or {}
        where_string, query_params = self.collect_where_string(_where_params)
        key = "total"
        stmt = f"SELECT COUNT(*) AS {key} FROM {self._table}"
        if where_string:
            stmt += f" WHERE {where_string}"
        result = await self.db_client.execute_stmt(stmt, params=query_params, only_one=True)
        return result[key]

    async def exists(
        self,
        where_params: dict[str, Any] | None = None,
    ) -> bool:
        _where_params = where_params or {}
        where_string, query_params = self.collect_where_string(_where_params)
        stmt = f"""
            SELECT EXISTS(
                SELECT 1
                FROM {self._table}
                {f"WHERE {where_string}" if where_string else ""}
            ) AS exists
        """.strip()
        result = await self.db_client.execute_stmt(
            stmt,
            params=query_params,
            only_one=True,
        )
        return bool(result["exists"])

    async def get_by_attributes(
        self,
        where_params: dict[str, Any] | None = None,
        joins: list[JoinParams] | None = None,
        order_fields: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[DtoSchemaType]:
        _where_params = where_params or {}
        _order_fields = order_fields or []
        _joins = joins or []
        where_string, where_params = self.collect_where_string(_where_params)
        join_string = self.collect_join_string(_joins)
        join_where_string, join_where_params = self.collect_join_where_string(_joins, where_params)
        order_string = self.collect_order_string(_order_fields)
        stmt = f"""
            SELECT {self._table}.*
            FROM {self._table} 
            {join_string} 
        """
        if where_string:
            stmt = stmt + f" WHERE {where_string} "
        if join_where_string:
            prefix = " WHERE " if not where_string else " "
            where_prefix = " AND " if not prefix else " "
            stmt = stmt + prefix + where_prefix + f" {join_where_string} "
        if order_string:
            stmt = stmt + f" ORDER BY {order_string} "
        if limit:
            stmt = stmt + f" LIMIT {limit} "
        if offset:
            stmt = stmt + f" OFFSET {offset} "
        stmt = stmt.strip()
        result = await self.db_client.execute_stmt(stmt, {**where_params, **join_where_params})
        return [self.dto_schema.model_validate(row) for row in result]

    async def get(self, pk_data: dict[str, Any]) -> DtoSchemaType | None:
        results = await self.get_by_attributes(where_params=pk_data, limit=2)
        if len(results) > 1:
            raise DatabaseMultiplyResultError(f"More than one result found - {results}")
        return self.dto_schema.model_validate(results[0]) if results else None

    async def update(
        self, pk_data: dict[str, Any], data: UpdateSchemaType, exclude_none: bool = False
    ) -> DtoSchemaType:
        where_string, where_params = self.collect_where_string(pk_data)
        set_data = data.model_dump(exclude_unset=True, exclude_none=False)
        if not set_data:
            raise ValueError("No values provided for update")
        set_params, set_parts = {}, []
        for key, value in set_data.items():
            param_key = f"set_{key}"  # чтобы не пересеклось с WHERE
            set_parts.append(f"{key} = :{param_key}")
            set_params[param_key] = value
        set_string = ", ".join(set_parts)
        query = f"""
            UPDATE {self._table}  
            SET {set_string} 
            WHERE {where_string} 
            RETURNING *
        """
        result = await self.db_client.execute_stmt(
            query, params={**where_params, **set_params}, external_session=self._session, only_one=True
        )
        if not result:
            raise DatabaseInstanceNotFoundError(f"Instance for remove not found. Params {pk_data}")
        return self.dto_schema.model_validate(result)

    async def remove(self, pk_data: dict[str, Any]) -> DtoSchemaType:
        where_string, query_params = self.collect_where_string(pk_data)
        query = f"""
            DELETE FROM {self._table} 
            WHERE {where_string} 
            RETURNING *
        """
        result = await self.db_client.execute_stmt(
            query, params=query_params, external_session=self._session, only_one=True
        )
        if not result:
            raise DatabaseInstanceNotFoundError(f"Instance for remove not found. Params {pk_data}")
        return self.dto_schema.model_validate(result)

    async def add(self, data: CreateSchemaType) -> DtoSchemaType:
        insert_values = data.model_dump()
        if not insert_values:
            raise ValueError("No values provided for insert")
        columns = ", ".join(insert_values.keys())
        values_placeholders = ", ".join(f":{key}" for key in insert_values)
        query = f"""
            INSERT INTO {self._table} ({columns})
            VALUES ({values_placeholders})
            RETURNING *
        """
        result = await self.db_client.execute_stmt(
            query, params=insert_values, external_session=self._session, only_one=True
        )
        return self.dto_schema.model_validate(result)

    async def add_batch(self, data: list[CreateSchemaType]) -> list[DtoSchemaType]:
        if not data:
            raise ValueError("No values provided for insert")
        schema = data[0]
        keys = schema.model_fields.keys()
        columns = ", ".join(keys)
        batch_size = self.MAX_ARGS // len(keys)
        all_results = []
        for i in range(0, len(data), batch_size):
            insert_data = [el.model_dump() for el in data[i : i + batch_size]]
            values_placeholders = [", ".join(f":{key}{ind}" for key in keys) for ind in range(len(insert_data))]
            values = {f"{key}{ind}": el[key] for key in keys for ind, el in enumerate(insert_data)}
            val_places = ", ".join([f"({el})" for el in values_placeholders])
            query = f"""
            INSERT INTO {self._table} ({columns})
            VALUES {val_places}
            RETURNING *
            """
            result = await self.db_client.execute_stmt(query, params=values, external_session=self._session)
            all_results.extend(result)
        return [self.dto_schema.model_validate(result) for result in all_results]

    def collect_where_string(
        self, params: dict[str, Any], already_collected_params: dict[str, Any] | None = None
    ) -> tuple[str, dict[str, Any]]:
        return self.__collect_where_string_from_repo(
            repo=self, params=params, already_collected_params=already_collected_params
        )

    def __collect_where_string_from_repo(
        self, repo: BaseRepository, params: dict[str, Any], already_collected_params: dict[str, Any] | None = None
    ) -> tuple[str, dict[str, Any]]:
        already_collected_params = already_collected_params or {}
        where_string = ""
        query_params: dict[str, Any] = {}
        and_strings = []
        if not params:
            return where_string, query_params
        key_counter: defaultdict[str, int] = defaultdict(int)
        model_keys = repo.dto_schema.model_fields.keys()
        for key, value in params.items():
            attr_name, *_lookup_suffix = key.rsplit(self.__LOOKUP_EXPRESSION_DEFAULT_SEPARATOR, maxsplit=1)
            if attr_name not in model_keys:
                raise AttributeError(f"{repo.dto_schema.__name__} dont have attribute {key}")
            lookup_suffix = _lookup_suffix[0] if _lookup_suffix else self.EQUAL_DEFAULT_LOOKUP_SUFFIX
            if lookup_suffix not in self.LOOKUP_EXPRESSION_OPERATOR_MAP:
                raise ValueError(f"The search expression suffix - {lookup_suffix} is not supported")
            operator = self.LOOKUP_EXPRESSION_OPERATOR_MAP[lookup_suffix]
            params_key = f"{key}_{key_counter[key]}"
            if params_key in already_collected_params:
                params_key = f"{key}_{key_counter[key]}"
            key_counter[key] += 1
            and_strings.append(f"{repo._table}.{attr_name} {operator} " + f":{params_key}")
            query_params[params_key] = value
        return " AND ".join(and_strings), query_params

    def collect_order_string(self, order_fields: list[str]) -> str:
        order_string = ""
        if not order_fields:
            return order_string
        order_parts = []
        attr_seen: set[str] = set()
        model_keys = self.dto_schema.model_fields.keys()
        for key in order_fields:
            attr_name, *_order_suffix = key.rsplit(self.__LOOKUP_EXPRESSION_DEFAULT_SEPARATOR, maxsplit=1)
            if attr_name not in model_keys:
                raise AttributeError(f"{self.dto_schema.__name__} dont have attribute {key}")
            if attr_name in attr_seen:
                raise ValueError("Duplicate attribute order")
            attr_seen.add(attr_name)
            order_suffix = _order_suffix[0] if _order_suffix else self.DEFAULT_ORDER_TYPE
            if order_suffix not in self.ORDER_PREFIX_MAP:
                raise ValueError(f"The order suffix - {order_suffix} is not supported, chose from {[*OrderTypes]}")
            order_parts.append(f"{self._table}.{attr_name} {self.ORDER_PREFIX_MAP[order_suffix]}".strip())
        return ", ".join(order_parts)

    @staticmethod
    def collect_join_string(
        joins: list[JoinParams],
    ) -> str:
        join_parts = []
        for join in joins:
            orig_table, joined_table = join.orig_repo._table, join.joined_repo._table
            on_parts = [f"{orig_table}.{cond.orig} {cond.operator} {joined_table}.{cond.joined}" for cond in join.on]
            on_string = " AND ".join(on_parts)
            join_sql = f"{join.join_type} JOIN {joined_table} ON {on_string}"
            join_parts.append(join_sql)
        return " ".join(join_parts)

    def collect_join_where_string(
        self, joins: list[JoinParams], already_collected_params: dict[str, Any] | None = None
    ) -> tuple[str, dict[str, Any]]:
        full_collected_params = already_collected_params or {}
        join_where_params = {}
        where_parts = []
        for join in joins:
            where_string, where_params = self.__collect_where_string_from_repo(
                repo=join.joined_repo, params=join.where or {}, already_collected_params=full_collected_params
            )
            if where_string:
                where_parts.append(where_string)
                join_where_params.update(where_params)
                full_collected_params.update(where_params)
        return " AND ".join(where_parts), join_where_params
