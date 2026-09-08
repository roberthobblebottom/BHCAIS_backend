from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from src.auth.jwthandler import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
)
from src.auth.users import change_password, get_password_hash, validate_user
from src.db.db_wrapper import engine
from src.Models import (
    ChangePasswordForm,
    CreateUserForm,
    DeleteUserForm,
    EditUserForm,
    passwordValidation,
)

router = APIRouter()


@router.post("/Login")
async def login(user: OAuth2PasswordRequestForm = Depends()):
    user = await validate_user(user)
    # user = None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"email": user[1], "user_type": user[3]},
        expires_delta=access_token_expires,  # user[1] is email
    )
    token = jsonable_encoder(access_token)
    content = {
        "message": "You've successfully logged in. Welcome back!",
        "email": user[1],  # user[1] is email
        "user_id": user[0],
        "user_type": user[3],  # user[3] == user type
        "token": token,
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


@router.get("/GetAllUsers")
async def get_all_users():
    with engine.begin() as connection:
        results = connection.execute(
            text("SELECT user_id,email,user_type FROM login_user;")
        ).all()
        print("results", {"results": [x._asdict() for x in results]})
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
        except IntegrityError:
            raise HTTPException(422, "Email already in the database.")

    return {"ok": True, "message": "successfully created a user"}


@router.post("/EditUser")
async def edit_user(form: EditUserForm):
    if (
        form.password != form.confirm_password
        and form.password != ""
        and form.confirm_new_password != ""
    ):
        raise HTTPException(
            422, "Password and confirm_passwords doesn't equate to each other"
        )
    if form.password != "" and form.confirm_new_password != "":
        passwordValidation(form.password)
        passwordValidation(form.confirm_password)

    with engine.begin() as connection:
        print("edit user", form.user_type.value)
        try:
            connection.execute(
                text("""UPDATE login_user 
                        SET 
                        email=:email,user_type=:user_type
                        WHERE login_user.user_id = :user_id
            """),
                [
                    {
                        "email": form.email,
                        "user_type": form.user_type.value,
                        "user_id": form.user_id,
                    }
                ],
            )
        except IntegrityError:
            raise HTTPException(422, "Email already in the database.")
    # with engine.begin() as connection:
    #     results = connection.execute(
    #         text("SELECT user_id,email,user_type FROM login_user;")
    #     ).all()
    #     print("results", {"results": [x._asdict() for x in results]})
    return {"ok": True, "message": "successfully Edit a user"}


@router.post("/DeleteUser")
async def delete_user(form: DeleteUserForm):
    user_id = form.user_id
    if user_id == None:
        raise HTTPException(422, "user_id is null")
    if user_id < 1:
        raise HTTPException(422, "user_id is less than one")
    with engine.begin() as connection:
        try:
            connection.execute(
                text("""
            DELETE FROM login_user WHERE user_id=:user_id
            """),
                [{"user_id": user_id}],
            )
        except Exception as exc:
            raise HTTPException(442, exc)
