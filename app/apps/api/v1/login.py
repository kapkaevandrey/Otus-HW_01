from http import HTTPStatus

from fastapi import APIRouter, Depends

from app.apps.api.utils import raise_http_exception_from_service_response
from app.core.containers import Context, get_context
from app.core.services import AuthUtils, UserService
from app.schemas.services import AuthUserServiceResponse, LoginUserData


auth_router = APIRouter()


@auth_router.post("/login", status_code=HTTPStatus.OK, response_model=AuthUserServiceResponse)
async def login_user(
    data: LoginUserData,
    context: Context = Depends(get_context),
) -> AuthUserServiceResponse:
    service = UserService(context)
    service_response = await service.login_user(data.id, data.password, AuthUtils())
    raise_http_exception_from_service_response(service_response)
    return service_response.result
