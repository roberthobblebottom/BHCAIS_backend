from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from src.db.db_wrapper import engine, text

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password.tobytes())


def get_password_hash(password):
    return pwd_context.hash(password)


async def _get_user(
    email: str,
):
    with engine.begin() as connection:
        result = connection.execute(
            text("""SELECT user_id, email,salted_password, user_type 
                    FROM login_user 
                    WHERE email = :email"""),
            [{"email": email}],
        )
    result = result.all()
    if len(result) == 0:  # can't find email
        raise Exception("Cant find email:", email)  # noqa: TRY002

    return result[0]  # first result


async def _set_login_tries(email: str, login_tries: int):
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                UPDATE login_user 
                WHERE email = :email 
                SET login_tries=:login_tries
                """,
                    [{"email": email, "login_tries": login_tries}],
                )
            )
    except:  # noqa: E722
        raise Exception("Cant find email:", email)  # noqa: TRY002


async def _get_login_tries(email: str):
    with engine.begin() as connection:
        result = connection.execute(
            text("""SELECT login_tries, ban_expiry 
                    FROM login_user 
                    WHERE email = :email"""),
            [{"email": email}],
        )
    result = result.one()
    print(result)
    if len(result) == 0:  # can't find email
        raise Exception("Cant find email:", email)  # noqa: TRY002

    return result[0]  # first result


async def _401_Exception(email: str, login_tries: int):
    login_tries += 1
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
    )
    await _set_login_tries(email, login_tries)


async def validate_user(
    user: OAuth2PasswordRequestForm = Depends(), enable_login_tries_count=False
):  # noqa: B008
    login_tries, ban_expiry = await _get_login_tries(user.username)
    print("login tries", login_tries)
    try:
        db_user = await _get_user(user.username)
    except Exception:
        _401_Exception(user.username, login_tries)
    if not verify_password(user.password, db_user[2]):  # salted_password from db
        _401_Exception(user.username, login_tries)

    return db_user


async def change_password(email: str, salted_password: str):
    salted_password = get_password_hash(salted_password)
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
    except Exception as e:  # noqa: BLE001
        raise Exception(e)  # noqa: TRY002
