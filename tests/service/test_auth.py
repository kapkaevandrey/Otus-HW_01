from http import HTTPStatus
from uuid import uuid4

import jwt
import pytest

from app.core.enums import ScopeType
from app.core.services import AuthUtils
from app.exceptions import BaseServiceError
from app.schemas.services import UserTokenData


@pytest.mark.parametrize("secret", [None, "secret"])
def test_get_user_data_from_jwt_valid(context, secret):
    jwt_secret = secret or "fake-secret"
    user_data = UserTokenData(sub=uuid4(), scope=ScopeType.ACCESS)
    jwt_token = jwt.encode(payload=user_data.model_dump(mode="json"), key=jwt_secret, algorithm="HS256")
    service = AuthUtils()
    expected_user_data = service.get_user_data_from_jwt(jwt_token, "HS256", secret)
    assert expected_user_data == user_data


@pytest.mark.parametrize(
    "token,secret,exception",
    [
        (
            "asd.sdfsd.sdfsdf",
            "secret",
            BaseServiceError(
                status=HTTPStatus.UNAUTHORIZED,
                error_message=AuthUtils.INVALID_TOKEN_FORMAT_MESSAGE.format(error="Error"),
            ),
        ),
        (
            "asd.sdfsd.sdfsdf",
            None,
            BaseServiceError(
                status=HTTPStatus.UNAUTHORIZED,
                error_message=AuthUtils.INVALID_TOKEN_FORMAT_MESSAGE.format(error="Error"),
            ),
        ),
        (
            "",
            "secret",
            BaseServiceError(
                status=HTTPStatus.UNAUTHORIZED,
                error_message=AuthUtils.INVALID_TOKEN_FORMAT_MESSAGE.format(error="Error"),
            ),
        ),
        (
            "",
            None,
            BaseServiceError(
                status=HTTPStatus.UNAUTHORIZED,
                error_message=AuthUtils.INVALID_TOKEN_FORMAT_MESSAGE.format(error="Error"),
            ),
        ),
        (
            jwt.encode(payload={"key": "value"}, key="secret", algorithm="HS256"),
            None,
            BaseServiceError(
                status=HTTPStatus.UNAUTHORIZED,
                error_message=AuthUtils.INVALID_JWT_PAYLOAD_MESSAGE,
            ),
        ),
        (
            jwt.encode(payload={"key": "value"}, key="secret", algorithm="HS256"),
            "fake_secret",
            BaseServiceError(
                status=HTTPStatus.UNAUTHORIZED,
                error_message=AuthUtils.INVALID_JWT_PAYLOAD_MESSAGE,
            ),
        ),
    ],
)
def test_get_user_data_from_jwt_invalid(context, token, secret, exception):
    service = AuthUtils()
    with pytest.raises(BaseServiceError) as exc:
        service.get_user_data_from_jwt(token, "HS256", secret)
        assert isinstance(exc, BaseServiceError)


@pytest.mark.parametrize(
    "token,secret",
    [
        (
            jwt.encode(payload={"key": "value"}, key="secret", algorithm="HS256"),
            "secret",
        ),
        (jwt.encode(payload={"key": "value"}, key="secret", algorithm="HS256"), None),
        (jwt.encode(payload={"key": "value"}, key="secret"), "secret"),
        ("qwerty.qwerqwr.qwerqwer", "secret"),
        ("qwerty.qwerqwr.qwerqwer", None),
        ("qwert", None),
        ("secret", None),
    ],
)
async def test_get_user_data_invalid_jwt(context, token, secret):
    service = AuthUtils()
    with pytest.raises(BaseServiceError):
        service.get_user_data_from_jwt(token, "HS256", secret)


@pytest.mark.parametrize("secret", ("secret", None))
async def test_get_user_data_valid_jwt(context, secret):
    service = AuthUtils()
    user_data = UserTokenData(sub=uuid4(), scope=ScopeType.ACCESS)
    token = jwt.encode(payload=user_data.model_dump(mode="json"), key="secret", algorithm="HS256")
    _user_data = service.get_user_data_from_jwt(token, "HS256", secret)
    assert _user_data == user_data


async def test_get_user_data_invalid_alg(context):
    secret = "secret"
    service = AuthUtils()
    user_data = UserTokenData(sub=uuid4(), scope=ScopeType.ACCESS)
    token = jwt.encode(payload=user_data.model_dump(mode="json"), key="secret", algorithm="HS256")
    with pytest.raises(BaseServiceError):
        service.get_user_data_from_jwt(token, "RS256", secret)
