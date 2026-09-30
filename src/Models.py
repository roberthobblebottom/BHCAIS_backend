import re
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import AfterValidator, BaseModel, EmailStr, Field

from src.constants import catalogue_names, passwordError, passwordRegex

router = APIRouter()


# Users
def password_validation(password: str) -> str:
    isValid = re.match(passwordRegex, password)
    base_path = Path(__file__).parent
    file_path = (base_path / "common-passwords.txt").resolve()
    with open(file_path, "r") as common_passwords:
        isValid = isValid and password not in common_passwords.read().split("\n")
    if not isValid:
        raise HTTPException(
            422, passwordError + " Or the password is a common password."
        )
    return password


class UserTypeEnum(str, Enum):
    admin = "admin"
    normal = "normal"


# Can't have enum for catalogue because print is a keyword and it will affect the enums operation
# class CatalogueEnum(str, Enum):
#     print_ = "print"
#     oral_history = "oral_history"
#     negative = "negative"
#     slide = "slide"
#     library_and_archive = "library_and_archive"
#     legacy_and_miscellaneous_items_report = "legacy_and_miscellaneous_items_report"


class ChangePasswordForm(BaseModel):
    username: EmailStr
    old_password: str
    new_password: Annotated[str, AfterValidator(password_validation)]
    confirm_new_password: Annotated[str, AfterValidator(password_validation)]
    token: str


class CreateUserForm(BaseModel):
    email: EmailStr
    password: Annotated[str, AfterValidator(password_validation)]
    confirm_password: Annotated[str, AfterValidator(password_validation)]
    user_type: UserTypeEnum
    token: str


class EditUserForm(BaseModel):
    user_id: int = Field(json_schema_extra=True)
    email: EmailStr
    password: Annotated[str, AfterValidator(password_validation)]
    confirm_password: Annotated[str, AfterValidator(password_validation)]
    user_type: UserTypeEnum
    token: str


class DeleteUserForm(BaseModel):
    user_id: int = Field(json_schema_extra=True)
    token: str


# FILES
class GetCatalogueModel(BaseModel):
    catalogue_name: Literal[*catalogue_names]
    rows_per_page: int = Field(ge=0)
    current_page_number: int = Field(ge=0)
    filter_str: str
    sort_by: str
    descending: bool
    token: str


class DownloadFilesModel(BaseModel):
    search_terms: dict
    selected_catalogues: list[Literal[*catalogue_names]]
    token: str


class DeleteSelectedRowsModel(BaseModel):
    ids_to_be_deleted: list[int, Field(json_schema_extra=True)]
    catalogue_name: Literal[*catalogue_names]
    current_primary_key: str
    token: str
