from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    print(plain_password,'\n',hashed_password)
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def get_user(username: str):
    # return await UserDatabaseSchema.from_queryset_single(Users.get(username=username))
    return {"username": "1", "password": "$2b$12$Q8u7yXiGRf78QreyknW00OCvkOKgmE1bUxMQSgC4Fwm4jlQVviqP6"}



async def validate_user(user: OAuth2PasswordRequestForm = Depends()):
    print('get password hash',get_password_hash('1'))
    try:
        db_user = await get_user(user.username)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        ) from exc
    print('here',type(user.password))
    # TODO HASHING OF PASSWORD
    if not verify_password(user.password, db_user['password']):
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
    )

    return db_user

