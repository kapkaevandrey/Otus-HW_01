from uuid import UUID

from app.schemas.base import EmptyBaseSchema


class RegisterUserServiceResponse(EmptyBaseSchema):
    user_id: UUID


class LoginUserData(EmptyBaseSchema):
    id: UUID
    password: str


class AuthUserServiceResponse(EmptyBaseSchema):
    token: UUID


class GetUserServiceResponse(EmptyBaseSchema):
    first_name: str
    second_name: str
    birthdate: str
    biography: str
    city: str
