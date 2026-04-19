from enum import StrEnum

from app.schemas.base import BaseModel


class JoinType(StrEnum):
    INNER = "INNER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class JoinCondition(BaseModel):
    orig: str
    operator: str = "="
    joined: str
