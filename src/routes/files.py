import json
from typing import Annotated

import polars as pl
from fastapi import APIRouter, File, HTTPException, UploadFile
from src.db.connect_db import engine, text
from sqlalchemy.exc import IntegrityError
from ..constants import (
    library_and_archives_header,
    negative_headers,
    oral_histories_headers,
    print_headers,
    slides_headers,
)

router = APIRouter()

# @router.post("/files")
# async def create_file(file: Annotated[bytes, File()]):
#     print("/files")
#     return {"file_size": len(file)}


@router.post("/uploadFiles")
async def create_upload_file(files: Annotated[list[UploadFile], File()], user_id: int):
    print("/uploadfile")
    print("user_id", user_id)

    results = []
    for file in files:
        print("file:", file.filename)
        print(file)
        contents = await file.read()
        catalog_name = ""

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
            raise HTTPException(
                status_code=422,
                detail="The file " + file.filename + "has incorrect or missing headers",
            )
        if cols == print_headers:
            catalog_name = "print"
            # fields not inserted yet:
            # object_condition,
            # main_category,
            # colletor,
            #  taken_locality ,
            # repository_location ,
            # catalogued_by1 ,
            #   catalogued_by2 ,
            #   catalogued_by3 ,
            #   access_level ,
            #   associated_negative_id ,
            # keywords,

            df_params = (
                df.select(
                    "UID",
                    "Album no.",
                    "Album Information (OLD)",
                    "Album Information (New)",
                    "Photograph Information",
                    "Day",
                    "Month",
                    "Year",
                    "Fieldnotes",
                    "Date catalogued",
                    "Remarks",
                    "Batch no.",
                )
                .with_columns(
                    upload_by=pl.lit(int(user_id)),
                    upload_date=pl.lit("NOW()"),
                )
                .with_columns(
                    # pl.concat_str(
                    #     pl.lit('{"album_number":'),
                    #     pl.col("Album no."),
                    #     pl.lit(',"album_information_old":'),
                    #     pl.col("Album Information (OLD)"),
                    #     pl.lit(',"album_information_new":"'),
                    #     pl.col("Album Information (New)")
                    #     .str.replace_all('"', "")
                    #     .str.replace_all("/", "", literal=True),
                    #     pl.lit('"}'),
                    # ).alias("album")
                )
                # .drop(
                #     "Album no.",
                #     "Album Information (OLD)",
                #     "Album Information (New)",
                # )
            )
            df_params.columns = [
                "uid",
                "Album no.",
                "Album Information (OLD)",
                "Album Information (New)",
                "photograph_label_info",
                "taken_day",
                "taken_month",
                "taken_year",
                "fieldnotes",
                "date_catalogued",
                "remarks",
                "batch_number",
                "upload_by",
                "upload_date",
            ]  # renaming
            # print(df_params["album"][0])
            df_params = (
                df_params.with_columns(pl.col("date_catalogued").str.split("||"))
                .with_columns(
                    pl.col("date_catalogued").list[0].alias("date_catalogued1"),
                    pl.col("date_catalogued").list[0].alias("date_catalogued2"),
                    pl.col("date_catalogued").list[0].alias("date_catalogued3"),
                )
                .to_dicts()
            )

            album_json = [
                json.dumps(
                    {
                        "album_number": row["Album no."],
                        "album_information_old": row["Album Information (OLD)"].replace(
                            '"', ""
                        ),
                        "album_information_new": row["Album Information (New)"]
                        .replace('"', "")
                        .replace("/", ""),
                    }
                )
                for row in df_params
            ]
            for dic, album in zip(df_params, album_json):
                dic["album"] = album
                del dic["Album no."]
                del dic["Album Information (OLD)"]
                del dic["Album Information (New)"]
            try:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            """INSERT INTO print (
                                uid  ,
                                photograph_label_info ,

                                taken_day ,
                                taken_month ,
                                taken_year ,
                                fieldnotes ,

                                remarks ,
                                batch_number ,
                                upload_by ,
                                upload_date,

                                date_catalogued1 ,
                                date_catalogued2 ,
                                date_catalogued3 ,

                                album 
                            )
                        VALUES
                            (
                              :uid  ,
                                :photograph_label_info ,

                                :taken_day ,
                                :taken_month ,
                                :taken_year ,
                                :fieldnotes ,

                          
                                :remarks ,
                                :batch_number ,
                                :upload_by ,
                                :upload_date,
                                :date_catalogued1 ,
                                :date_catalogued2 ,
                                :date_catalogued3 ,
                                :album
                            ) """
                        ),
                        df_params,
                    )
                    print(connection.execute(text("select * from print")).all())
            except IntegrityError as e:
                error_string = str(e)
                formatted_error_message = ""
                if "UniqueViolation" in error_string:
                    formatted_error_message = (
                        "You have uploaded rows with non unique s/n"
                    )
                else:
                    formatted_error_message = error_string
                raise HTTPException(
                    status_code=422,
                    detail=formatted_error_message,
                )
        elif cols == negative_headers:
            catalog_name = "negative"
        elif cols == oral_histories_headers:
            catalog_name = "oral histories"
        elif cols == library_and_archives_header:
            catalog_name = "library and archives"
        elif cols == slides_headers:
            catalog_name = "slides"
        else:
            raise HTTPException(
                status_code=422, detail="unable to decipher the catalog type"
            )

        # print("catalog_name", catalog_name)
        # print(df.describe())

        results.append({"filename": file.filename})
    return {"uploaded_files": results}
