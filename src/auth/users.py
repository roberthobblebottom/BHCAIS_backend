from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from src.db.db_wrapper import engine, text

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    # pwd_context.
    return pwd_context.verify(plain_password, hashed_password.tobytes())


def get_password_hash(password):
    return pwd_context.hash(password)


async def _get_user(
    username: str,
):
    with engine.begin() as connection:
        result = connection.execute(
            text("""SELECT user_id, email,salted_password, user_type 
        FROM login_user 
        WHERE email = :username;"""),
            [{"username": username}],
        )
    result = result.all()
    if len(result) == 0:  # can't find email
        raise Exception("Cant find username:", username)  # noqa: TRY002

    return result[0]  # first result


async def validate_user(user: OAuth2PasswordRequestForm = Depends()):
    try:
        db_user = await _get_user(user.username)
    except Exception as exc:
        print("1")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        ) from exc
    # print("user password", user.password)
    # print("db_user [2] salted password from db", db_user[2])
    # print("a new password hash", get_password_hash(user.password))
    if not verify_password(user.password, db_user[2]):  # salted_password from db
        print("2")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

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
