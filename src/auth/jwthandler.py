import os
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Header, HTTPException, Request
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2, OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from src.db.db_wrapper import does_admin_exist_in_db, does_user_exist_in_db

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class OAuth2PasswordBearerCookie(OAuth2):
    """
    Args:
        OAuth2 (OAuth2): OAuth2 Model
    """

    def __init__(
        self,
        token_url: str,
        scheme_name: str | None = None,
        scopes: dict | None = None,
        auto_error: bool = True,
    ):
        """
        Args:
            token_url (str):
            scheme_name (str | None, optional):  Defaults to None.
            scopes (dict | None, optional):  Defaults to None.
            auto_error (bool, optional):  Defaults to True.
        """
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": token_url, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> str | None:
        """

        Args:
            request (Request): Request Object that has the auth header

        Raises:
            HTTPException: 401, Not Authenticated

        Returns:
            str | None: params
        """
        authorization: str = request.cookies.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)

        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None

        return param


security = OAuth2PasswordBearerCookie(token_url="/Login")


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Args:
        data (dict): data to encode
        expires_delta (timedelta | None, optional): when it expires. Defaults to None, which will adds 15 minutes.

    Returns:
        str: Encoded JWT
    """
    to_encode = data.copy()

    expire_timestamp = (
        datetime.now(UTC) + expires_delta
        if expires_delta
        else datetime.now(UTC) + timedelta(minutes=15)
    )

    to_encode.update({"exp": expire_timestamp})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def route_auth_by_token(header: Annotated[str, Header()]):
    """
    Args:
        header (Annotated[str, Header): packet header with the authentication token
    Raises:
        credentials_exception: 401 "Could not Validate Credential"
    Returns:
        str: Email String
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    print("route auth by token")

    # Extract bearer token from header
    try:
        scheme, token = header.split()
        if scheme.lower() != "bearer":
            print("scheme does not have bearer")
            raise credentials_exception
    except ValueError:
        print("Value error on auth split")
        raise credentials_exception
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            print("if email is none")
            raise credentials_exception
        if not does_user_exist_in_db(email):
            print("if user does not exist in db")
            raise credentials_exception
    except JWTError:
        print("JWT Error")
        raise credentials_exception

    print("auth success")
    return email


def admin_route_auth_by_token(header: Annotated[str, Header()]):
    """

    Args:
        header (Annotated[str, Header): packet header with the authentication token

    Raises:
        credentials_exception: 401 "Could not Validate Credential"

    Returns:
        str: Email String
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    print("admin route auth by token")

    # Extract bearer token from header
    try:
        scheme, token = header.split()
        if scheme.lower() != "bearer":
            print("scheme does not have bear")
            raise credentials_exception
    except ValueError:
        print("Value error on auth split")
        raise credentials_exception

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        user_type: str = payload.get("user_type")
        if user_type != "admin":
            print("user type is not admin")
            raise credentials_exception
        if email is None or user_type is None:
            print("if email is none or user_type is none")
            raise credentials_exception
        if not does_admin_exist_in_db(email):
            print("if user does not exist in db")
            raise credentials_exception
    except JWTError:
        print("JWT Error")
        raise credentials_exception

    print("auth success")
    return email
