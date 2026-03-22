from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.apps.api.utils import raise_http_exception_from_service_response
from app.core.consts import STRING_COLUMN_255
from app.core.containers import Context, get_context
from app.core.services import AuthUtils, UserService
from app.schemas.services import GetUserServiceResponse, RegisterUserData, RegisterUserServiceResponse
from app.schemas.types import NotEmptyString


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


@users_router.get("/search", status_code=HTTPStatus.OK, response_model=list[GetUserServiceResponse])
async def search_users(
    first_name: NotEmptyString = Query(max_length=STRING_COLUMN_255),
    last_name: NotEmptyString = Query(max_length=STRING_COLUMN_255),
    context: Context = Depends(get_context),
) -> list[GetUserServiceResponse]:
    service = UserService(context)
    service_response = await service.search_users(first_name, last_name)
    raise_http_exception_from_service_response(service_response)
    return service_response.result
