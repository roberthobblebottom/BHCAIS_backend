import re
from datetime import timedelta
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import AfterValidator, BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from src.auth.jwthandler import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
)
from src.auth.users import change_password, get_password_hash, validate_user
from src.constants import passwordError, passwordRegex
from src.db.db_wrapper import engine

router = APIRouter()


def passwordValidation(password: str) -> str:
    isValid = re.match(passwordRegex, password)

    if not isValid:
        raise HTTPException(422, passwordError)
    return password


class ChangePasswordForm(BaseModel):
    username: EmailStr
    old_password: str
    new_password: Annotated[str, AfterValidator(passwordValidation)]
    confirm_new_password: Annotated[str, AfterValidator(passwordValidation)]


class UserTypeEnum(str, Enum):
    admin = "admin"
    normal = "normal"


class CreateUserForm(BaseModel):
    email: EmailStr
    password: Annotated[str, AfterValidator(passwordValidation)]
    confirm_password: Annotated[str, AfterValidator(passwordValidation)]
    user_type: UserTypeEnum


@router.post("/Login")
async def login(user: OAuth2PasswordRequestForm = Depends()):
    print("login function")
    user = await validate_user(user)
    print("user", user)
    # user = None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user[1]},
        expires_delta=access_token_expires,  # user[1] is email
    )
    token = jsonable_encoder(access_token)
    content = {
        "message": "You've successfully logged in. Welcome back!",
        "email": user[1],  # user[1] is email
        "user_id": user[0],
        "user_type": user[3],  # user[3] == user type
    }
    response = JSONResponse(content=content)
    response.set_cookie(
        "Authorization",
        value=f"Bearer {token}",
        httponly=True,
        max_age=1800,
        expires=1800,
        samesite="Lax",
        secure=False,
    )

    return response


@router.post("/ChangePassword")
async def change_password_route(form: ChangePasswordForm):
    print("change password route")
    if (
        form.new_password != form.confirm_new_password
        or form.new_password == ""
        or form.confirm_new_password == ""
        or form.old_password == ""
        or form.username == ""
    ):
        raise HTTPException(422, "password form is mulformed in some way")
    try:
        await validate_user(
            OAuth2PasswordRequestForm(
                username=form.username, password=form.old_password
            )
        )

        await change_password(form.username, form.new_password)
    except HTTPException as exc:
        if exc.status_code == 401:
            raise HTTPException(422, "Incorrect username or password.") from exc
        raise HTTPException(422, "password form is mulformed in some way")
    return {"ok": True, "message": "sucessfully changed the password"}


@router.get("/GetAllUsers", status_code=200)
async def get_all_users():
    with engine.begin() as connection:
        results = connection.execute(
            text("SELECT user_id,email,user_type FROM login_user;")
        ).all()
        return {"results": [x._asdict() for x in results]}


@router.post("/CreateUser")
async def create_user(form: CreateUserForm):
    if form.password != form.confirm_password:
        raise HTTPException(
            422, "Password and confirm_passwords doesn't equate to each other"
        )
    with engine.begin() as connection:
        try:
            connection.execute(
                text("""INSERT INTO login_user 
                        (email,salted_password,user_type) 
                        VALUES (:email,:salted_password,:user_type)
            """),
                [
                    {
                        "email": form.email,
                        "salted_password": get_password_hash(form.password),
                        "user_type": form.user_type.value,
                    }
                ],
            )
        except IntegrityError as exc:
            raise HTTPException(422, "Email already in the database.")
    return {"ok": True, "message": "successfully created a user"}


# @router.get(
#     "/users/whoami", response_model=UserOutSchema, dependencies=[Depends(get_current_user)]
# )
# async def read_users_me(current_user: UserOutSchema = Depends(get_current_user)):
#     return current_user


# @router.delete(
#     "/user/{user_id}",
#     response_model=Status,
#     responses={404: {"model": HTTPNotFoundError}},
#     dependencies=[Depends(get_current_user)],
# )
# async def delete_user(
#     user_id: int, current_user: UserOutSchema = Depends(get_current_user)
# ) -> Status:
#     return await crud.delete_user(user_id, current_user)
