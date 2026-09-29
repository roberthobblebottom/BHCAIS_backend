import re
from enum import Enum

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import AfterValidator, BaseModel, EmailStr, Field
from src.constants import passwordError, passwordRegex, catalogue_names

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
    catalogue_name: Literal[*catalogue_names]
    rows_per_page: int = Field(ge=0)
    current_page_number: int = Field(ge=0)
    filter_str: str
    sort_by: str
    descending: bool
    token: str


class DownloadFilesModel(BaseModel):
    # date_range: list[str]
    search_terms: dict
    selected_catalogues: list[Literal[*catalogue_names]]
    token: str


class DeleteSelectedRowsModel(BaseModel):
    ids_to_be_deleted: list[int, Field(primary_key=True)]
    catalogue_name: list[Literal[*catalogue_names]]
    current_primary_key: str
    token: str
