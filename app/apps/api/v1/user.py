from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends

from app.apps.api.utils import raise_http_exception_from_service_response
from app.core.containers import Context, get_context
from app.core.services import AuthUtils, UserService
from app.schemas.services import GetUserServiceResponse, RegisterUserData, RegisterUserServiceResponse


users_router = APIRouter(prefix="/user")


@users_router.post("/register", status_code=HTTPStatus.OK, response_model=RegisterUserServiceResponse)
async def register_user(
    data: RegisterUserData,
    context: Context = Depends(get_context),
) -> RegisterUserServiceResponse:
    service = UserService(context)
    service_response = await service.register_user(data, AuthUtils())
    raise_http_exception_from_service_response(service_response)
    return service_response.result


@users_router.get("/get/{user_id}", status_code=HTTPStatus.OK, response_model=GetUserServiceResponse)
async def get_user(
    user_id: UUID,
    context: Context = Depends(get_context),
) -> GetUserServiceResponse:
    service = UserService(context)
    service_response = await service.get_user(user_id)
    raise_http_exception_from_service_response(service_response)
    return service_response.result
