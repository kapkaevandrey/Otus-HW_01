from typing import Annotated

from pydantic import AfterValidator


def not_empty_string(value: str) -> str:
    if not value.strip():
        raise ValueError("Value cant be empty string")
    return value


NotEmptyString = Annotated[str, AfterValidator(not_empty_string)]
