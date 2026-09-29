import re
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import AfterValidator, BaseModel, EmailStr, Field
from src.constants import passwordError, passwordRegex

router = APIRouter()


# Users
def passwordValidation(password: str) -> str:
    isValid = re.match(passwordRegex, password)

    if not isValid:
        raise HTTPException(422, passwordError)
    return password


class UserTypeEnum(str, Enum):
    admin = "admin"
    normal = "normal"


class CatalogueEnum(str, Enum):
    print = "print"


class ChangePasswordForm(BaseModel):
    username: EmailStr
    old_password: str
    new_password: Annotated[str, AfterValidator(passwordValidation)]
    confirm_new_password: Annotated[str, AfterValidator(passwordValidation)]
    token: str


class CreateUserForm(BaseModel):
    email: EmailStr
    password: Annotated[str, AfterValidator(passwordValidation)]
    confirm_password: Annotated[str, AfterValidator(passwordValidation)]
    user_type: UserTypeEnum
    token: str


class EditUserForm(BaseModel):
    user_id: int = Field(primary_key=True)
    email: EmailStr
    password: str
    confirm_password: str
    user_type: UserTypeEnum
    token: str


class DeleteUserForm(BaseModel):
    user_id: int = Field(primary_key=True)
    token: str


# FILES


class GetCatalogueModel(BaseModel):
    catalogue_name: str
    rows_per_page: int
    current_page_number: int
    filter_str: str
    sort_by: str
    descending: bool
    token: str


class DownloadFilesModel(BaseModel):
    # date_range: list[str]
    search_terms: dict
    selected_catalogues: list[str]
    token: str


class DeleteSelectedRowsModel(BaseModel):
    ids_to_be_deleted: list[int, Field(primary_key=True)]
    catalogue_name: str
    current_primary_key: str
    token: str
