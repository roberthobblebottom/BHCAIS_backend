import json
from typing import Annotated

import polars as pl
from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from src.db.db_wrapper import (
    df_params_sorting_of_names_and_id_in_list_fields,
    df_params_sorting_of_names_and_ids,
    engine,
    find_if_locality_name_exists_in_db,
    get_all_people_from_person_table,
    get_unique_localities,
    insert_into_locality,
    insert_into_person_if_not_exist_in_name_held,
    localities_params_dict_sorting_of_names_and_ids,
    text,
)

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
            #############################################
            #############################################
            #############################################
        if cols == print_headers:
            catalog_name = "print"
            # fields not inserted yet:

            #   associated_negative_id ,
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
                "Catalogued by",
                "Date catalogued",
                "Access status",
                "Remarks",
                "Batch no.",
            ).with_columns(
                uploaded_by_user_of_id=pl.lit(int(user_id)),
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
                "repository_location_id",
                "catalogued_by_names",
                "dates_catalogued",
                "access_level",
                "remarks",
                "batch_number",
                "uploaded_by_user_of_id",
                "upload_date",
            ]  # renaming
            df_params = df_params.with_columns(
                pl.col("dates_catalogued").str.strip_chars().str.split("||"),
                pl.col("catalogued_by_names").str.strip_chars().str.split("||"),
            )

            unique_collectors_names = df_params["collector_name"].unique().to_list()
            unique_sets_of_cataloguer_names = (
                df_params["catalogued_by_names"].unique().to_list()
            )
            unique_country_names = df_params["country"].unique().to_list()
            unique_localities = (
                df_params["locality", "country", "gps_coordinates"]
                .filter(~pl.col("locality").str.to_lowercase().is_in(["nil", "na"]))
                .unique()
            )
            unique_repository_location_ids = (
                df_params["repository_location_id"].unique().to_list()
            )
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
            # for dic, album in zip(params_dict, album_json):
            #     dic["album"] = album
            #     del dic["album_number"]
            #     del dic["album_information_old"]
            #     del dic["album_information_new"]
            #     del dic["country"]
            #     del dic["gps_coordinates"]
            df_params = pl.concat(
                [df_params, pl.DataFrame(album_json, schema={"album": pl.String})],
                how="horizontal",
            )
            try:
                with engine.begin() as connection:
                    # Collectors and catalogurs ---------------------------------------------

                    for name in unique_collectors_names:
                        insert_into_person_if_not_exist_in_name_held(
                            name, user_id, connection
                        )

                    for name in unique_sets_of_cataloguer_names:
                        insert_into_person_if_not_exist_in_name_held(
                            name, user_id, connection
                        )

                    # Get all people including collectors just added.
                    people = get_all_people_from_person_table(connection)

                    # change the collector_name into collector-id in params_dict and catagoluers_name into cataloger_ids in params_dict
                    df_params = df_params_sorting_of_names_and_ids(
                        df_params, people, "collector", "name_held", "person"
                    )

                    df_params = df_params_sorting_of_names_and_id_in_list_fields(
                        df_params, people, "catalogued_by", "name_held", "person_id"
                    )
                    print(df_params)
                    # for x in params_dict:
                    #     hasCataloguersByIDsChanged = False
                    #     new_catalogued_by_ids = []
                    #     for person in people:
                    #         for cataloguer_name in x["catalogued_by_ids"]:
                    #             if cataloguer_name not in person[1]:
                    #                 # 1 index points to name_held in person
                    #                 new_catalogued_by_ids.append(
                    #                     person[0]
                    #                 )  # persion_id in people
                    #                 hasCataloguersByIDsChanged = True
                    #     x["catalogued_by_ids"] = (
                    #         new_catalogued_by_ids
                    #         if hasCataloguersByIDsChanged
                    #         else None
                    #     )
                    # Locality --------------------------------------------------------
                    # insert any new country locality into locality table
                    for locality in unique_country_names:
                        result = find_if_locality_name_exists_in_db(
                            locality, connection
                        )
                        if result is None:
                            insert_into_locality(
                                {
                                    "locality_name": locality,
                                    "locality_rank": "country",
                                    "parent_locality": None,
                                    "uploaded_by_user_of_id": user_id,
                                    "upload_date": "NOW()",
                                },
                                connection,
                            )

                    # Get all countries even the one that are just added
                    countries = get_unique_localities(
                        where="WHERE locality_rank = 'country'", connection=connection
                    )
                    # countries = [[locality id, locality name]] USE INDICES
                    # insert any new locality  into the locality table
                    for locality in (
                        unique_localities.iter_rows()
                    ):  # [locality (place name), country, gps coords ] USE INDICES
                        result = find_if_locality_name_exists_in_db(
                            locality[0], connection
                        )
                        if result is None:
                            # get all country id in roles for specific locations insertion entries to be inserted right below
                            country_id = -1
                            for c in countries:
                                if (
                                    c[1] == locality[1]
                                ):  # locality_name on both side of the equation
                                    country_id = c[0]
                                ###############################
                                (
                                    insert_into_locality(
                                        {
                                            "locality_name": locality[0],
                                            "locality_rank": "place",
                                            "parent_locality": country_id,
                                            "uploaded_by_user_of_id": user_id,
                                            "upload_date": "NOW()",
                                        },
                                        connection,
                                    ),
                                )

                    # insert any new repository locations
                    for locality in unique_repository_location_ids:
                        result = find_if_locality_name_exists_in_db(
                            locality, connection
                        )
                        if result is None:
                            insert_into_locality(
                                {
                                    "locality_name": locality,
                                    "locality_rank": "repository location",
                                    "parent_locality": 2,  # For NUS
                                    "uploaded_by_user_of_id": user_id,
                                    "upload_date": "NOW()",
                                },
                                connection,
                            )

                    # get all localities including the ones just added
                    unique_localities = get_unique_localities(connection=connection)
                    unique_localities = pl.DataFrame(
                        unique_localities, schema=["locality_id", "locality_name"]
                    )

                    # change locality name to locality id for "locality" and "repository_locality" in params_dict
                    df_params = localities_params_dict_sorting_of_names_and_ids(
                        df_params, unique_localities, "locality"
                    )
                    df_params = localities_params_dict_sorting_of_names_and_ids(
                        df_params,
                        unique_localities,
                        "repository_location_id",
                    )
                    params_dict = df_params.to_dicts()
                    print(params_dict[0])
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
                                taken_locality_id,
                                fieldnotes ,
                                keywords,

                               repository_location_id,
                                access_level,
                                remarks ,
                                batch_number ,
                                uploaded_by_user_of_id ,
                                upload_date,
                                catalogued_by_ids,
                                dates_catalogued ,
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
                            :repository_location_id,
                            :access_level,
                            :remarks ,
                            :batch_number ,
                            :uploaded_by_user_of_id ,
                            :upload_date,

                            :catalogued_by_ids,
                            :dates_catalogued ,
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
        #############################################
        #############################################
        #############################################
        elif cols == oral_histories_headers:
            catalog_name = "oral histories"
            df_params = df.select(
                "S/N",
                "Name of Interviewee",
                "Name of Interviewee (2)",
                "Recording Date (DD/MM/YYYY)",
                "Track Number",
                "Total Tracks",
                "Running Time",
                "File name",
                "Format (Original File)",
                "Access Conditions",
                "Access Remarks",
                "Transcription Status",
                "Editing Remarks",
                "Vetted for Access?",
                "Accession Status",
                "Languages",
                "Keywords",
                "Interview Location",
                "Interviewers",
                "Associated Materials",
                "Catalogued By",
                "Catalogue Date",
                "Comments",
            ).with_columns(
                uploaded_by_user_of_id=pl.lit(int(user_id)),
                upload_date=pl.lit("NOW()"),
            )
            df_params.columns = [
                "sn",
                "name_of_interviewee1",
                "name_of_interviewee2",
                "recording_date",
                "track_number",
                "total_tracks",
                "track_duration",
                "file_name",
                "file_format",
                "access_condition",
                "access_remarks",
                "transcription_status",
                "track_editing_remarks",
                "was_vetted_for_access",
                "accession_status",
                "primary_language",
                "keywords",
                "interview_location_name",
                "interviewer_names",
                "associated_materials",
                "catalogued_by",
                "catalogued_date",
                "comments",
                "uploaded_by_user_of_id",
                "upload_date",
            ]  # renaming

            df_params = df_params.with_columns(
                interviewer_names=pl.col("interviewer_names")
                .str.strip_chars()
                .str.split(","),
                interviewee_names=pl.concat_list(
                    "name_of_interviewee1", "name_of_interviewee2"
                ),
            )

            unique_interview_participant_names = (
                df_params["interviewer_names"].explode().unique().to_list()
                + df_params["interviewee_names"].explode().unique().to_list()
            )
            unique_interview_participant_names = [
                x for x in unique_interview_participant_names if x is not None
            ]
            unique_localities = (
                df_params.filter(pl.col("interview_location_name").is_not_null())[
                    "interview_location_name"
                ]
                .unique()
                .to_list()
            )

            try:
                with engine.begin() as connection:
                    # Insert new interviewers if it does not exist
                    for name in unique_interview_participant_names:
                        insert_into_person_if_not_exist_in_name_held(
                            name, user_id, connection
                        )
                    people = get_all_people_from_person_table(connection)
                    df_params = df_params.with_columns()
                    df_params = df_params_sorting_of_names_and_id_in_list_fields(
                        df_params, people, "interviewee", "name_held", "person_id"
                    )
                    df_params = df_params_sorting_of_names_and_id_in_list_fields(
                        df_params, people, "interviewer", "name_held", "person_id"
                    )
                    # locality
                    for locality in unique_localities:
                        results = find_if_locality_name_exists_in_db(
                            locality, connection
                        )
                        if results is None:
                            insert_into_locality(
                                {
                                    "locality_name": locality,
                                    "locality_rank": "place",
                                    "parent_locality": None,
                                    "uploaded_by_user_of_id": user_id,
                                    "upload_date": "NOW()",
                                },
                                connection,
                            )

                    unique_localities = pl.DataFrame(
                        get_unique_localities(where=None, connection=connection),
                    )

                    # change locality name to locality id for "locality" and "repository_locality" in params_dict
                    df_params = df_params_sorting_of_names_and_ids(
                        df_params,
                        unique_localities,
                        "interview_location",
                        "locality_name",
                        "locality",
                    )
                    df_grouped = df_params.with_columns(
                        pl.col("track_duration")
                        .str.split(" ")
                        .list[1]
                        .alias("track_duration")
                    ).group_by(["interviewer_ids", "interviewee_ids", "total_tracks"])
                    df_grouped = (
                        df_grouped.agg(
                            "file_name",
                            "recording_date",
                            "track_duration",
                            "access_condition",
                            "access_remarks",
                            "primary_language",
                            "interview_location_id",
                            "comments",
                        )
                        .with_columns(
                            uploaded_by_user_of_id=pl.lit(int(user_id)),
                            upload_date=pl.lit("NOW()"),
                        )
                        .with_columns(
                            pl.col(pl.List(pl.String())).list.agg(
                                pl.element().drop_nulls().drop_nans().unique()
                            ),
                            pl.col(pl.List(pl.Int64())).list.agg(
                                pl.element().drop_nans().drop_nulls().unique()
                            ),
                            pl.col(pl.List(pl.Int16())).list.agg(
                                pl.element().drop_nans().drop_nulls().unique()
                            ),
                        )
                        .with_columns(
                            pl.col(
                                "track_duration",
                                "recording_date",
                                "file_name",
                                "access_condition",
                                "access_condition",
                                "access_remarks",
                                "primary_language",
                                "comments",
                            ).list.join(","),
                            ### this block for interview_location_id must be done twice or else out of bounce error will occur:
                            pl.when(
                                (pl.col("interview_location_id").list.len() == 0)
                                | (pl.col("interview_location_id").is_null())
                            )
                            .then(pl.lit(None))
                            .otherwise("interview_location_id")
                            .alias("interview_location_id"),
                        )
                    )
                    # print(df_grouped.dtypes)
                    # print(
                    #     df_grouped.filter(
                    #         pl.col("interview_location_id").is_not_null()
                    #     ).select("interview_location_id")
                    # )
                    df_grouped = df_grouped.with_columns(
                        pl.when(pl.col("primary_language") == "")
                        .then(pl.lit("NULL"))
                        .otherwise("primary_language")
                        .alias("primary_language"),
                        pl.when(pl.col("interviewer_ids").list.len() == 0)
                        .then(pl.lit(None))
                        .otherwise("interviewer_ids")
                        .alias("interviewer_ids"),
                        pl.when(pl.col("interviewee_ids").list.len() == 0)
                        .then(pl.lit(None))
                        .otherwise("interviewee_ids")
                        .alias("interviewee_ids"),
                        ### this block for interview_location_id must be done twice or else out of bounce error will occur:
                        pl.when(
                            (pl.col("interview_location_id").list.len() == 0)
                            | (pl.col("interview_location_id").is_null())
                        )
                        .then(pl.lit(None))
                        .otherwise(
                            pl.col("interview_location_id").list[0]
                        )  # GET THE FIRST INTERVIEW LOCATION ID
                        .alias("interview_location_id"),
                    )

                    # retur
                    # Main insertion into Oral table table
                    connection.execute(
                        text(
                            """INSERT INTO oral_history_track (
                                    track_number ,
                                    file_name ,
                                    file_format ,
                                    track_duration ,
                                    date_of_recording ,
                                    track_transcription_complete ,
                                    track_editing_remarks ,
                                    track_comments ,
                                    access_condition ,
                                    catalogued_by ,
                                    catalogued_date ,
                                    upload_date ,
                                    uploaded_by_user_of_id
                            ) VALUES (
                                    :track_number ,
                                    :file_name ,
                                    :file_format ,
                                    :track_duration ,
                                    :recording_date ,
                                    :transcription_status,
                                    :track_editing_remarks ,
                                    :comments ,
                                    :access_condition ,
                                    :catalogued_by ,
                                    :catalogued_date ,
                                    :upload_date ,
                                    :uploaded_by_user_of_id
                            ) """
                        ),
                        df_params.to_dicts(),
                    )

                    connection.execute(
                        text(
                            """
                        INSERT INTO oral_history
                       (   
                            interview_name ,
                            recording_date ,
                            total_tracks ,
                            total_run_time ,
                            access_condition ,
                            access_remarks ,
                            primary_language, 
                            interview_location_id ,
                            interviewer_ids ,
                            interviewee_ids ,
                            comments ,
                            uploaded_by_user_of_id,
                            upload_date 
                        ) VALUES(
                            :file_name ,
                            :recording_date ,
                            :total_tracks ,
                            :track_duration ,
                            :access_condition ,
                            :access_remarks ,
                            :primary_language ,
                            :interview_location_id ,
                            :interviewer_ids ,
                            :interviewee_ids ,
                            :comments ,
                            :uploaded_by_user_of_id,
                            :upload_date 
                        )
                                                    """
                        ),
                        df_grouped.to_dicts(),
                    )

                    # # Main insertion into Oral table track table
                    # connection.execute(
                    #     text(
                    #         """INSERT INTO oral_history_track (
                    #                            interviewID ,
                    #                             track_number ,
                    #                             file_name ,
                    #                             file_path ,
                    #                             file_format ,
                    #                             transcript_path ,
                    #                             track_duration ,
                    #                             date_of_recording ,
                    #                             track_transcription_complete ,
                    #                             track_editing_remarks ,
                    #                             track_comments ,
                    #                             access_level,
                    #                             catalogued_by ,
                    #                             catalogued_date ,
                    #                             upload_date ,
                    #                             uploaded_by_user_of_id
                    #                     ) VALUES (
                    #                             :interviewID ,
                    #                             :track_number ,
                    #                             :file_name ,
                    #                             :file_path ,
                    #                             :file_format ,
                    #                             :transcript_path ,
                    #                             :track_duration ,
                    #                             :date_of_recording ,
                    #                             :track_transcription_complete ,
                    #                             :track_editing_remarks ,
                    #                             :track_comments ,
                    #                             :access_level,
                    #                             :catalogued_by ,
                    #                             :catalogued_date ,
                    #                             :upload_date ,
                    #                             :uploaded_by_user_of_id
                    #                     ) """
                    #     ),
                    #     params_dict,
                    # )
            except IntegrityError as e:
                pass

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
        results = []
        results.append({"filename": file.filename})
    return {"uploaded_files": results}
