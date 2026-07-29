from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

# from src.schemas.token import Status
# from .schemas.users import UserInSchema, UserOutSchema
from src.auth.jwthandler import (
    # get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
)

# from tortoise.contrib.fastapi import HTTPNotFoundError
# import src.crud.users as crud
from src.auth.users import validate_user

router = APIRouter()


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
        data={"sub": user[0]}, expires_delta=access_token_expires
    )
    token = jsonable_encoder(access_token)
    content = {
        "message": "You've successfully logged in. Welcome back!",
        "email": user[0],
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
