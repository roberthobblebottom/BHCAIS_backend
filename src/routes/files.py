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

            # catalogued_by1 ,
            #   catalogued_by2 ,
            #   catalogued_by3 ,
            #   associated_negative_id ,
            # keywords,
            # taxonomy
            # common name

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
                "Location in LKCNHM",
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
                "repository_location",
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
            unique_repository_locations = (
                df_params["repository_location"].unique().to_list()
            )
            # print("unique_collectors_names", unique_collectors_names)
            # print("unique_country_names", unique_country_names)
            # print("unique_locality", unique_locality)
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

                    # Insert new collector if it does not exist
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

                    # Get all people including collectors just added.
                    people = list(
                        connection.execute(
                            text("SELECT person_id, name_held FROM person")
                        ).all()
                    )

                    # change the collector_name into collector-id in params_dict
                    for x in params_dict:
                        hasLocalityChanged = False
                        for unique_collector in people:
                            if (
                                x["collector_name"] in people[1].name_held
                            ):  # name_held in people
                                x["collector_id"] = people[0][0]  # persion_id in people
                                hasLocalityChanged = True
                                break
                            if not hasLocalityChanged:
                                x["collector_id"] = None
                        del x["collector_name"]

                    # Locality --------------------------------------------------------
                    # insert any new country locality into locality table
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

                    # Get all countries even the one that are just added
                    countries = connection.execute(
                        text("""
                                SELECT DISTINCT locality_id, locality_name
                                FROM locality
                                WHERE locality_rank = 'country';""")
                    ).all()
                    # countries = [[locality id, locality name]] USE INDICES

                    # insert any new locality  into the locality table
                    for locality in (
                        unique_locality.iter_rows()
                    ):  # [locality (place name), country, gps coords ] USE INDICES
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
                        if result is None:
                            # add country_id into the new locality entry

                            # get all country id in roles for specific locations insertion entries to be inserted right below
                            country_id = -1
                            for c in countries:
                                if (
                                    c[1] == locality[1]
                                ):  # locality_name on both side of the equation
                                    country_id = c[0]
                            ###############################
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

                    # insert any new repository locations
                    for locality in unique_repository_locations:
                        print("location name", locality)
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
                            print("result is None")
                            connection.execute(
                                text(
                                    """
                                    INSERT INTO locality (locality_name,locality_rank,parent_locality,upload_by,upload_date)
                                    VALUES (:locality_name,:locality_rank,:parent_locality,:upload_by,:upload_date)
                                    """
                                ),
                                [
                                    {
                                        "locality_name": locality,
                                        "locality_rank": "place",
                                        "parent_locality": 2,  # For NUS
                                        "upload_by": user_id,
                                        "upload_date": "NOW()",
                                    }
                                ],
                            )
                    # get all localities including the ones just added
                    unique_locality = connection.execute(
                        text("SELECT DISTINCT locality_id,locality_name FROM locality")
                    ).all()
                    unique_locality = pl.DataFrame(
                        unique_locality, schema=["locality_id", "locality_name"]
                    )

                    # change locality name to locality id for "locality" in params_dict
                    for x in params_dict:
                        hasLocalityChanged = False
                        hasRepositoryLocationChanged = False
                        for l in unique_locality.iter_rows():
                            if x["locality"] == l[1]:  # locality (name)
                                x["locality"] = l[0]  # locality_id
                                hasLocalityChanged = True
                                # break
                            if x["repository_location"] == l[1]:
                                x["repository_location"] = l[0]
                                hasRepositoryLocationChanged = True

                        if not hasLocalityChanged:
                            x["locality"] = None
                        if not hasRepositoryLocationChanged:
                            x["repository_location"] = None

                    # Main insertion into print table
                    connection.execute(
                        text(
                            """INSERT INTO print (
                                uid  ,
                                object_condition,
                                photograph_label_info ,
                                main_category,
                                taken_day ,
                                taken_month ,
                                taken_year ,
                                taken_locality,
                                fieldnotes ,
                                keywords,

                               repository_location, 
                                access_level,
                                remarks ,
                                batch_number ,
                                upload_by ,
                                upload_date,
                                date_catalogued ,
                                album,
                                collector_id
                            )
                        VALUES
                            (
                              :uid  ,
                            :object_condition,
                            :photograph_label_info ,
                            :main_category,
                            :taken_day ,
                            :taken_month ,
                            :taken_year ,
                            :locality,
                            :fieldnotes ,
                            :keywords,
                            :repository_location,
                            :access_level,
                            :remarks ,
                            :batch_number ,
                            :upload_by ,
                            :upload_date,
                            
                            :date_catalogued ,
                            :album,
                            :collector_id
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
