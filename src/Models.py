import re
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import AfterValidator, BaseModel, EmailStr
from src.constants import passwordError, passwordRegex

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
