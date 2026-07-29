from typing import Annotated

import polars as pl
from fastapi import APIRouter, File, HTTPException, UploadFile

from ..constants import (
    library_and_archives_header,
    negative_headers,
    oral_histories_headers,
    print_headers,
    slides_headers,
)

router = APIRouter()


@router.post("/files")
async def create_file(file: Annotated[bytes, File()]):
    print("/files")
    return {"file_size": len(file)}


@router.post("/uploadFiles")
async def create_upload_file(files: Annotated[list[UploadFile], File()]):
    print("/uploadfile")
    results = []
    for file in files:
        print("file:", file.filename)
        print(file)
        contents = await file.read()
        if ".xlsx" in file.filename:
            df = pl.read_excel(contents, infer_schema_length=0)
        elif ".csv" in file.filename:
            df = pl.read_csv(contents, infer_schema_length=0)
        else:
            raise HTTPException(
                status_code=422,
                details="The file " + file.filename + " is not in .csv or .xlsx",
            )

        if df.shape[0] <= 1:
            raise HTTPException(
                status_code=422,
                detail="The file "
                + file.filename
                + " is either empty or only contains header",
            )
        cols = str([col.lower().strip() for col in df.columns])
        if (
            cols != print_headers
            and cols != oral_histories_headers
            and cols != slides_headers
            and cols != negative_headers
            and cols != library_and_archives_header
        ):
            print("here")
            raise HTTPException(
                status_code=422,
                detail="The file " + file.filename + "has incorrect or missing headers",
            )
        print(df.describe())

        results.append({"filename": file.filename})
    print("results", results)
    return {"uploaded_files": results}
