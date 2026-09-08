import re
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AfterValidator, BaseModel, EmailStr
from src.auth.jwthandler import route_auth_by_token
from src.constants import passwordError, passwordRegex

router = APIRouter()


# Users
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


class EditUserForm(BaseModel):
    user_id: int
    email: EmailStr
    password: str
    confirm_password: str
    user_type: UserTypeEnum


class DeleteUserForm(BaseModel):
    user_id: int


# FILES
class DownloadFilesModel(BaseModel):
    # date_range: list[str]
    search_terms: dict
    selected_catalogues: list[str]
    token: str


class DeleteSelectedRowsModel(BaseModel):
    ids_to_be_deleted: list[str]
    catalogue_name: str
    current_primary_key: str
    token: str
