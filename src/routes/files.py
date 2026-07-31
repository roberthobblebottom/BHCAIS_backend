import json
from typing import Annotated

import polars as pl
from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from src.db.connect_db import engine, text

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
            #  taken_locality ,
            # repository_location ,
            # catalogued_by1 ,
            #   catalogued_by2 ,
            #   catalogued_by3 ,
            #   associated_negative_id ,
            # keywords,
            # taxonomy
            # common name
            # Locality
            # GPS coordinates
            # Location in LKCNHM
            df_params = df.select(
                "UID",
                "Album no.",
                "Object Condition (QC1)",
                "Album Information (OLD)",
                "Album Information (New)",
                "Photograph Information",
                "Main Category",
                "Collector's Name",
                "Day",
                "Month",
                "Year",
                "Country",
                "Locality",
                "GPS Coordinates",
                "Fieldnotes",
                "Keywords",
                "Date catalogued",
                "Access status",
                "Remarks",
                "Batch no.",
            ).with_columns(
                upload_by=pl.lit(int(user_id)),
                upload_date=pl.lit("NOW()"),
            )
            df_params.columns = [
                "uid",
                "album_number",
                "object_condition",
                "album_information_old",
                "album_information_new",
                "photograph_label_info",
                "main_category",
                "collector_name",
                "taken_day",
                "taken_month",
                "taken_year",
                "country",
                "locality",
                "gps_coordinates",
                "fieldnotes",
                "keywords",
                "date_catalogued",
                "access_level",
                "remarks",
                "batch_number",
                "upload_by",
                "upload_date",
            ]  # renaming
            df_params = df_params.with_columns(
                pl.col("date_catalogued").str.split("||")
            )

            unique_collectors_names = df_params["collector_name"].unique().to_list()
            unique_country_names = df_params["country"].unique().to_list()
            unique_locality = (
                df_params["locality", "country", "gps_coordinates"]
                .filter(~pl.col("locality").str.to_lowercase().is_in(["nil", "na"]))
                .unique()
            )
            print("unique_collectors_names", unique_collectors_names)
            print("unique_country_names", unique_country_names)
            print("unique_locality", unique_locality)
            params_dict = df_params.to_dicts()
            album_json = [
                json.dumps(
                    {
                        "album_number": row["album_number"],
                        "album_information_old": row["album_information_old"].replace(
                            '"', ""
                        ),
                        "album_information_new": row["album_information_new"]
                        .replace('"', "")
                        .replace("/", ""),
                    }
                )
                for row in params_dict
            ]
            for dic, album in zip(params_dict, album_json):
                dic["album"] = album
                del dic["album_number"]
                del dic["album_information_old"]
                del dic["album_information_new"]
                del dic["country"]
                del dic["gps_coordinates"]
            try:
                with engine.begin() as connection:
                    # Collectors ---------------------------------------------
                    unique_collectors = []
                    for name in unique_collectors_names:
                        result = connection.execute(
                            text(
                                "SELECT 1 FROM person WHERE :name=ANY(name_held) LIMIT 1;"
                            ),
                            [{"name": name}],
                        ).first()

                        if result is None:
                            connection.execute(
                                text(
                                    """
                                    INSERT INTO person (name_held,upload_by,upload_date)
                                    VALUES (ARRAY [:name_held],:upload_by,:upload_date)
                                    """
                                ),
                                [
                                    {
                                        "name_held": name,
                                        "upload_by": user_id,
                                        "upload_date": "NOW()",
                                    }
                                ],
                            )
                            person_id = connection.execute(
                                text("SELECT LASTVAL();")
                            ).one()
                            unique_collectors.append(
                                {"person_id": person_id[0], "name_held": name}
                            )
                    print("unique_collectors", unique_collectors)
                    for x in params_dict:
                        for unique_collector in unique_collectors:
                            if x["collector_name"] == unique_collector["name_held"]:
                                x["collector_id"] = unique_collector["person_id"]
                                break

                    # Locality --------------------------------------------------------
                    for locality in unique_country_names:
                        result = connection.execute(
                            text(
                                """
                                SELECT 1
                                FROM locality
                                WHERE locality_name = :locality_name
                                LIMIT 1;
                                """
                            ),
                            [{"locality_name": locality}],
                        ).first()

                        if result is None:
                            connection.execute(
                                text(
                                    """
                                    INSERT INTO locality (locality_name,locality_rank,upload_by,upload_date)
                                    VALUES (:locality_name,:locality_rank,:upload_by,:upload_date)
                                    """
                                ),
                                [
                                    {
                                        "locality_name": locality,
                                        "locality_rank": "country",
                                        "upload_by": user_id,
                                        "upload_date": "NOW()",
                                    }
                                ],
                            )
                    countries = connection.execute(
                        text("""
                                SELECT DISTINCT locality_id, locality_name
                                FROM locality
                                WHERE locality_rank = 'country';""")
                    ).all()
                    # countries = [[locality id, locality name]] USE INDICES
                    print("countries", countries)
                    # --------- main locality logic -------
                    for locality in (
                        unique_locality.iter_rows()
                    ):  # [locality (place name), country, gps coords ] USE INDICES
                        # print("locality", locality)
                        result = connection.execute(
                            text(
                                """
                                SELECT 1
                                FROM locality
                                WHERE locality_name = :locality_name
                                LIMIT 1;
                                """
                            ),
                            [{"locality_name": locality[0]}],
                        ).first()
                        # print("result", result)
                        if result is None:
                            country_id = -1
                            for c in countries:
                                if c[1] == locality[1]:
                                    country_id = c[0]
                            connection.execute(
                                text(
                                    """
                                    INSERT INTO locality (locality_name,locality_rank,parent_locality,upload_by,upload_date)
                                    VALUES (:locality_name,:locality_rank,:parent_locality,:upload_by,:upload_date)
                                    """
                                ),
                                [
                                    {
                                        "locality_name": locality[0],
                                        "locality_rank": "place",
                                        "parent_locality": country_id,
                                        "upload_by": user_id,
                                        "upload_date": "NOW()",
                                    }
                                ],
                            )

                            # print("locality_id", locality_id)
                    unique_locality = connection.execute(
                        text("SELECT DISTINCT locality_id,locality_name FROM locality")
                    ).all()
                    unique_locality = pl.DataFrame(
                        unique_locality, schema=["locality_id", "locality_name"]
                    )
                    print("unique_locality", unique_locality)
                    for x in params_dict:
                        # print("x locality", x["locality"])
                        original = x["locality"]
                        hasChange = False
                        for l in unique_locality.iter_rows():
                            # print(x["locality"], l[0], l[-1])
                            if x["locality"] == l[1]:  # locality (name)
                                x["locality"] = l[0]  # locality_id
                                hasChange = True
                                break
                        if not hasChange:
                            x["locality"] = None

                        # if x["locality"] == -1:
                        #     print(x)
                        # print("original", original, "update", x["locality"])
                    connection.execute(
                        text(
                            """INSERT INTO print (
                                uid  ,
                                object_condition,
                                photograph_label_info ,

                                main_category,
                                collector,
                                    taken_day ,
                                    taken_month ,
                                taken_year ,
                                taken_locality,
                                fieldnotes ,
                                keywords,

                                access_level,
                                remarks ,
                                batch_number ,
                                upload_by ,
                                upload_date,

                                date_catalogued ,
                                album

                            )
                        VALUES
                            (
                              :uid  ,

                                :object_condition,
                                :photograph_label_info ,

                                :main_category,
                                :collector_id,
                                :taken_day ,
                                :taken_month ,
                                :taken_year ,
                                :locality,
                                :fieldnotes ,
                                :keywords,

                                :access_level,
                                :remarks ,
                                :batch_number ,
                                :upload_by ,
                                :upload_date,
                                :date_catalogued ,

                                :album
                            ) """
                        ),
                        params_dict,
                    )

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
