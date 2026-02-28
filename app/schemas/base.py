from typing import TypeVar

from pydantic import BaseModel, ConfigDict


DataT = TypeVar("DataT")


class EmptyBaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @property
    def is_empty(self):
        return all(getattr(self, field) is None for field in self.model_fields)
