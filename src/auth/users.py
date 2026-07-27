from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from src.db.connect_db import text, connection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password.tobytes())


def get_password_hash(password):
    return pwd_context.hash(password)


async def get_user(
    username: str,
):
    connection.execute(text("SET search_path TO public"))
    result = connection.execute(
        text("select email,salted_password from login_user WHERE email = :username;"),
        [{"username": username}],
    )
    result = result.all()
    if len(result) == 0:  # can't find email
        raise Exception
    print("db result", result)

    return result[0]  # first result


async def validate_user(user: OAuth2PasswordRequestForm = Depends()):
    try:
        db_user = await get_user(user.username)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        ) from exc
    if not verify_password(user.password, db_user[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    return db_user
