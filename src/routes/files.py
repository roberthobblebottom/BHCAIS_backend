from typing import Annotated

import polars as pl
from fastapi import APIRouter, File, HTTPException, UploadFile

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
            df = pl.read_excel(contents)
        elif ".csv" in file.filename:
            df = pl.read_csv(contents)
        else:
            raise HTTPException(
                status_code=422,
                details="The file " + file.filename + " is not in .csv or .xlsx",
            )

        if df.size[0] <= 1:
            raise HTTPException(
                status_code=422,
                detail="The file "
                + file.filename
                + " is either empty or only contains header",
            )
        print(df.describe())

        results.append({"filename": file.filename})
    print("results", results)
    return {"uploaded_files": results}
