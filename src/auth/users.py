import math
from datetime import UTC, datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy.exc import ResourceClosedError
from src.db.db_wrapper import engine, text

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SINGAPORE_TIMEZONE = timezone(timedelta(hours=8))

"""user functions for authentication with Database accesses and/or modifications
    """


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password.tobytes())


def get_password_hash(password):
    return pwd_context.hash(password)


async def _get_user(
    email: str,
):
    """

    Args:
        email (str): email to identify user

    Raises:
        err: Resource Closed Error, Cant find email

    Returns:
        Sequence[Row[_TP]]: user details
    """
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""SELECT user_id, email,salted_password, user_type 
                        FROM login_user 
                        WHERE email = :email"""),
                [{"email": email}],
            )
            result = result.all()
    except ResourceClosedError as err:
        raise err("Cant find email:", email)

    return result[0]  # first result


async def _set_login_tries(
    email: str, login_tries: int, ban_expiry_date: datetime | None = None
):
    """Set login tries and ban expiry of a user

    Args:
        email (str): email to identify user
        login_tries (int): number of log in tries by this user
        ban_expiry_date (datetime | None, optional): new ban expiry date of this user. Defaults to None.

    Raises:
        err: Resource Closed Error, Cant find email
    """
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                UPDATE login_user 
                SET login_tries=:login_tries,
                    ban_expiry_date = :ban_expiry_date
                WHERE email = :email 
                """,
                ),
                [
                    {
                        "email": email,
                        "login_tries": login_tries,
                        "ban_expiry_date": ban_expiry_date,
                    }
                ],
            )
    except ResourceClosedError as err:
        raise err("Cant find email:", email)


async def _get_login_tries_from(email: str):
    """_summary_

    Args:
        email (str): _description_

    Raises:
        err: Resource Closed Error, Cant find email
        HTTPException: To raise that the user account is now locked.

    Returns:
        int: login_tires
    """
    with engine.begin() as connection:
        try:
            result = connection.execute(
                text("""SELECT login_tries, ban_expiry_date 
                    FROM login_user 
                    WHERE email = :email"""),
                [{"email": email}],
            )
            result = list(result.one())
        except ResourceClosedError as err:
            raise err("Cant find email:", email)

        login_tries = result[0] if result[0] is not None else 0

        ban_expiry_date = (
            result[1].replace(tzinfo=SINGAPORE_TIMEZONE)
            if result[1] is not None
            else None
        )

        if ban_expiry_date is None:
            return login_tries
        if datetime.now(UTC).astimezone(SINGAPORE_TIMEZONE) < ban_expiry_date:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Because of too many incorrect password attempts, You have been locked till "
                + (ban_expiry_date).strftime("%d-%m-%Y %H:%M:%S"),
            )
        else:
            await _set_login_tries(email, 0, None)
            return login_tries


async def _401_Exception(email: str, login_tries: int, enable_login_tries_count=False):
    """Throws 401 Error

    Args:
        email (str): email to identify user
        login_tries (int): number of log in tries by this user
        enable_login_tries_count (bool, optional): _description_. Defaults to False.
    Raises:
        HTTPException: Incorrect username or password.  shows number of tries
        HTTPException: Tells user that there is too many incorrect credentials authentication attempts and user is banned to a date
        HTTPException: Incorrect username or password.  shows number of tries
    """
    if not enable_login_tries_count:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password. Number of tries:"
            + str(login_tries),
        )
    login_tries += 1

    if login_tries % 3 == 0:
        extra_minutes = 5 * math.floor(login_tries / 3)
        ban_expiry_date = datetime.now(UTC).astimezone(SINGAPORE_TIMEZONE) + timedelta(
            minutes=extra_minutes
        )

        await _set_login_tries(email, login_tries, ban_expiry_date)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Because of too many incorrect email or password attempts, You have been banned till "
            + (ban_expiry_date).strftime("%d-%m-%Y %H:%M:%S"),
        )

    await _set_login_tries(email, login_tries)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password. Number of tries:" + str(login_tries),
    )


async def validate_user(
    user: OAuth2PasswordRequestForm = Depends(),  # noqa: B008
    enable_login_tries_count=False,
):
    """Validate User if it exist

    Args:
        user (OAuth2PasswordRequestForm, optional): user and user password Model. Defaults to Depends().
        enable_login_tries_count(bool): Defaults to False,
    Raises:
        await: calls error helper class for Resource closed error: can't find said user
        await: _description_

    Returns:
        _type_: user
    """
    if enable_login_tries_count:
        login_tries = await _get_login_tries_from(user.username)

    try:
        db_user = await _get_user(user.username)
    except ResourceClosedError:
        raise await _401_Exception(user.username, login_tries, enable_login_tries_count)
    if not verify_password(user.password, db_user[2]):  # salted_password from db
        raise await _401_Exception(user.username, login_tries, enable_login_tries_count)

    return db_user


async def change_password(email: str, unsalted_password: str):
    """

    Args:
        email (str): email that identifies user
        unsalted_password (str): unsalted password string to be salted and inserted

    Raises:
        err: ResourceClosedError, no such user.
    """
    salted_password = get_password_hash(unsalted_password)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
            UPDATE login_user SET salted_password=:salted_password WHERE email = :email 
            """),
                [
                    {
                        "email": email,
                        "salted_password": salted_password,
                    }
                ],
            )
    except ResourceClosedError as err:
        raise err()
