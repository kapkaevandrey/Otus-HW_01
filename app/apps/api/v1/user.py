from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.containers import Context, get_context
from app.core.services import AuthUtils, UserService
from app.schemas.dto import UserCreateSchema
from app.schemas.services import GetUserServiceResponse, RegisterUserServiceResponse


users_router = APIRouter(prefix="/user")


@users_router.get("/register", status_code=HTTPStatus.OK, response_model=RegisterUserServiceResponse)
async def register_user(
    data: UserCreateSchema,
    context: Context = Depends(get_context),
) -> RegisterUserServiceResponse:
    service = UserService(context)
    service_response = await service.register_user(data, AuthUtils())
    return service_response.result


@users_router.get("/get/{user_id}", status_code=HTTPStatus.OK, response_model=GetUserServiceResponse)
async def get_user(
    user_id: UUID,
    context: Context = Depends(get_context),
) -> GetUserServiceResponse:
    service = UserService(context)
    service_response = await service.get_user(user_id)
    return service_response.result
