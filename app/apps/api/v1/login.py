from http import HTTPStatus

from fastapi import APIRouter, Depends

from app.core.containers import Context, get_context
from app.core.services import AuthUtils, UserService
from app.schemas.services import AuthUserServiceResponse, LoginUserData


auth_router = APIRouter()


@auth_router.get("/login", status_code=HTTPStatus.OK, response_model=AuthUserServiceResponse)
async def login_user(
    data: LoginUserData,
    context: Context = Depends(get_context),
) -> AuthUserServiceResponse:
    service = UserService(context)
    service_response = await service.login_user(data.id, data.password, AuthUtils())
    return service_response.result
