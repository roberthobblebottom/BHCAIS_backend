from datetime import timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.exc import (
    IntegrityError,
    NoSuchColumnError,
    NoSuchTableError,
    ResourceClosedError,
)
from src.auth.jwthandler import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    admin_route_auth_by_token,
    create_access_token,
)
from src.auth.users import (
    change_password,
    get_password_hash,
    validate_user,
)
from src.db.db_wrapper import engine
from src.Models import (
    ChangePasswordForm,
    CreateUserForm,
    DeleteUserForm,
    EditUserForm,
)

router = APIRouter()


@router.post("/Login")
async def login(user: OAuth2PasswordRequestForm = Depends()):  # noqa: B008
    """_summary_

    Args:
        user (OAuth2PasswordRequestForm, optional): _description_. Defaults to Depends().

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    user = await validate_user(user, True)
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
    time = 1800 * 100  # 50 Hours
    response.set_cookie(
        "Authorization",
        value=f"Bearer {token}",
        httponly=True,
        max_age=time,
        expires=time,
        samesite="Lax",
        secure=False,
    )

    return response


@router.put("/ChangePassword")
async def change_password_route(
    form: ChangePasswordForm, email: str = Depends(admin_route_auth_by_token)
):
    """

    Args:
        form (ChangePasswordForm): _description_
        email (str, optional): _description_. Defaults to Depends(admin_route_auth_by_token).

    Raises:
        HTTPException: raises If form misses some attributes or new password not equals confirm new password
        HTTPException: raises if Incorrect User name or password. 401 c-> 422
        HTTPException: raises If form misses some attributes or new password not equals confirm new password
        HTTPException: raise If no such table, no such column or no so such email

    Returns:
        _type_: _description_
    """
    if (
        form.new_password != form.confirm_new_password
        or form.new_password == ""
        or form.confirm_new_password == ""
        or form.old_password == ""
        or form.username == ""
    ):
        raise HTTPException(
            422,
            "password form is mulformed in some way. form may have misses some attributes or new password not equals confirm new password",
        )
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
        raise HTTPException(
            422,
            "password form is mulformed in some way. form may have misses some attributes or new password not equals confirm new password",
        )
    except (NoSuchTableError, NoSuchColumnError, ResourceClosedError) as e:
        raise HTTPException(500, e)
    return {"ok": True, "message": "sucessfully changed the password"}


@router.get("/GetAllUsers")
async def get_all_users(email: str = Depends(admin_route_auth_by_token)):
    """Admin Function to Get All Users

    Args:
        email (str, optional): email used to determine if user is an admin. Defaults to Depends(admin_route_auth_by_token).

    Raises:
        HTTPException: raise If no such table, no such column or no so such email

    Returns:
         Sequence[Row[_TP]]: User details
    """
    try:
        with engine.begin() as connection:
            results = connection.execute(
                text("SELECT user_id,email,user_type FROM login_user")
            ).all()
            return {"results": [x._asdict() for x in results]}
    except (NoSuchTableError, NoSuchColumnError, ResourceClosedError) as e:
        raise HTTPException(500, e)


@router.post("/CreateUser")
async def create_user(
    form: CreateUserForm, email: str = Depends(admin_route_auth_by_token)
):
    """Admin Function to create new user

    Args:
        form (CreateUserForm): details for the creation of user.
        email (str, optional): email used to determine if user is an admin. Defaults to Depends(admin_route_auth_by_token).

    Raises:
        HTTPException: password and confirm_password is not equal.
        HTTPException: Email already in database
        HTTPException: raise If no such table, no such column or no so such email

    Returns:
        dict: message that user is sucessfully created.
    """
    if (
        form.password != form.confirm_password
        and form.password != ""
        and form.confirm_password != ""
    ):
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
        except (NoSuchTableError, NoSuchColumnError, ResourceClosedError) as e:
            raise HTTPException(500, e)

    return {"ok": True, "message": "successfully created a user"}


@router.put("/EditUser")
async def edit_user(
    form: EditUserForm = Body(...),  # noqa: B008
    email: str = Depends(admin_route_auth_by_token),
):
    """Admin Function for editing user details

    Args:
        form (EditUserForm, optional): data model for the editing of user details. Defaults to Body(...).
        email (str, optional): email used to determine if user is an admin. Defaults to Depends(admin_route_auth_by_token).

    Raises:
        HTTPException: password and confirm_password is not equal.
        HTTPException: Email already in database
        HTTPException: raise If no such table, no such column or no so such email

    Returns:
        dict: message that user is sucessfully created.
    """
    if (
        form.password != form.confirm_password
        and form.password != ""
        and form.confirm_password != ""
    ):
        raise HTTPException(
            422, "Password and confirm_passwords doesn't equate to each other"
        )

    with engine.begin() as connection:
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

            if form.password != "":
                p = get_password_hash(form.password)
                connection.execute(
                    text("""UPDATE login_user 
                        SET 
                        salted_password=:salted_password
                        WHERE login_user.user_id = :user_id
                    """),
                    [
                        {
                            "salted_password": p,
                            "user_id": form.user_id,
                        }
                    ],
                )
        except IntegrityError:
            raise HTTPException(422, "Email already in the database.")
        except (NoSuchTableError, NoSuchColumnError, ResourceClosedError) as e:
            raise HTTPException(500, e)
    return {"ok": True, "message": "successfully Edit a user"}


@router.delete("/DeleteUser")
async def delete_user(
    form: DeleteUserForm, email: str = Depends(admin_route_auth_by_token)
):
    """Admin Function to delete user.

    Args:
        form (DeleteUserForm): user form that contains user id for identify user to be deleted.
        email (str, optional): email used to determine if user is an admin. Defaults to Depends(admin_route_auth_by_token).

    Raises:
        HTTPException: user id is null; invalid
        HTTPException: user id is less than one; invalid
        HTTPException: raise If no such table, no such column or no so such email

    """
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
        except (NoSuchTableError, NoSuchColumnError, ResourceClosedError) as e:
            raise HTTPException(500, e)
