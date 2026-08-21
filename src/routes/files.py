import json  # noqa: I001
from typing import Annotated

import polars as pl
from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import literal_column, bindparam
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
    libraryAndArchiveHeader,
    negativeHeaders,
    oralHistoryHeaders,
    printHeaders,
    slideHeaders,
    get_header_dict,
)
from pydantic import BaseModel
from fastapi.responses import FileResponse

router = APIRouter()


class DeleteSelectedRowsModel(BaseModel):
    ids_to_be_deleted: list[int]
    catalogue_name: str


class DownloadFilesModel(BaseModel):
    # date_range: list[str]
    search_term: str
    selected_catalogues: list[str]


@router.get("/getCatalogue", status_code=200)
async def getCatalogue(
    catalogue_name: str,
    rows_per_page: int,
    current_page_number: int,
    filter_str: str,
    sort_by: str,
    descending: bool,
):
    filter_str = "%" + filter_str + "%" if filter_str != "" else ""

    with engine.begin() as connection:
        row_counts = connection.execute(
            text(f"""
            SELECT COUNT(*) FROM {catalogue_name}_raw;
        """)
        ).one()[0]
        fetchCount = row_counts if rows_per_page == 0 else rows_per_page

        startRow = (current_page_number - 1) * rows_per_page

        where_sql_condition = ""
        if filter_str != "":
            for i, x in enumerate(get_header_dict[catalogue_name]):
                keyword = "WHERE" if i == 0 else "OR"
                where_sql_condition += (
                    f" {keyword} {literal_column(x)} ILIKE :filter_str{i}"
                )
        order_by_sql_condition = (
            f"ORDER BY {literal_column(sort_by)}"
            if sort_by not in ["desc", "null"]
            else ""
        )
        order_by_sql_condition = (
            order_by_sql_condition + " DESC"
            if descending and order_by_sql_condition != ""
            else ""
        )
        sql = (
            f"SELECT * FROM {literal_column(catalogue_name)}_raw "
            + where_sql_condition
            + order_by_sql_condition
            + " LIMIT :fetch_count OFFSET :start_row;"
        )
        print("sql", sql)
        params = {
            "sort_by": sort_by,
            "fetch_count": fetchCount,
            "start_row": startRow,
        }
        if filter_str != "":
            for x in range(len(get_header_dict[catalogue_name])):
                params[f"filter_str{x}"] = filter_str
        print("params", params)
        results = [
            row._asdict()
            for row in connection.execute(
                text(sql),
                [params],
            ).all()
        ]
        print("results", results)
        return {"results": results, "row_counts": row_counts}


@router.post("/uploadFiles")
async def create_upload_file(files: Annotated[list[UploadFile], File()], user_id: int):
    is_futher_processing_disabled = True
    results = []
    for file in files:
        contents = await file.read()

        # Checking of validity of the files:
        if ".xlsx" in file.filename:
            df = pl.read_excel(contents, infer_schema_length=0)
        elif ".csv" in file.filename:
            df = pl.read_csv(contents, infer_schema_length=0)
            while "" in df.columns:
                df = df.drop("")
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
        cols = str([col.lower().strip() for col in df.columns if col != ""])
        print("cols", cols)
        if (
            cols != printHeaders
            and cols != oralHistoryHeaders
            and cols != slideHeaders
            and cols != negativeHeaders
            and cols != libraryAndArchiveHeader
        ):
            raise HTTPException(
                status_code=422,
                detail="The file " + file.filename + "has incorrect or missing headers",
            )
        ### Individual Catalogue processing
        if cols == printHeaders:
            # Raw Insertion
            df_raw = df.clone()
            df_raw.columns = [
                "continuous_sn_no",
                "uid",
                "album_no",
                "object_condition_qc1",
                "album_information_old",
                "album_information_new",
                "photograph_information",
                "main_category",
                "collector_name",
                "day",
                "month",
                "year",
                "country",
                "locality",
                "gps_coordinates",
                "taxonomy",
                "common_name",
                "fieldnotes",
                "keywords",
                "location_in_lkcnhm",
                "catalogued_by",
                "catalogued_date",
                "access_status",
                "remarks",
                "negative_yn",
                "batch_no",
                "sign_out_date",
                "sign_in_date",
                "date_of_qc",
                "checked_by",
                "object_condition_qc2",
            ]
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                            INSERT INTO print_raw (
                                        continuous_sn_no ,
                                        uid ,
                                        album_no ,
                                        object_condition_qc1 ,
                                        album_information_old ,
                                        album_information_new ,
                                        photograph_information  ,
                                        main_category  ,
                                        collector_name ,
                                        day ,
                                        month ,
                                        year ,
                                        country ,
                                        locality ,
                                        gps_coordinates ,
                                        taxonomy ,
                                        common_name ,
                                        fieldnotes ,
                                        keywords ,
                                        location_in_lkcnhm ,
                                        catalogued_by ,
                                       catalogued_date ,
                                        access_status ,
                                        remarks ,
                                        negative_yn ,
                                        batch_no ,
                                        sign_out_date ,
                                        sign_in_date ,
                                        date_of_qc ,
                                        checked_by ,
                                        object_condition_qc2 
                            ) VALUES (
                              :continuous_sn_no ,
                                        :uid ,
                                        :album_no ,
                                        :object_condition_qc1 ,
                                        :album_information_old ,
                                        :album_information_new ,
                                        :photograph_information  ,
                                        :main_category  ,
                                        :collector_name ,
                                        :day ,
                                        :month ,
                                        :year ,
                                        :country ,
                                        :locality ,
                                        :gps_coordinates ,
                                        :taxonomy ,
                                        :common_name ,
                                        :fieldnotes ,
                                        :keywords ,
                                        :location_in_lkcnhm ,
                                        :catalogued_by ,
                                        :catalogued_date ,
                                        :access_status ,
                                        :remarks ,
                                        :negative_yn ,
                                        :batch_no ,
                                        :sign_out_date ,
                                        :sign_in_date ,
                                        :date_of_qc ,
                                        :checked_by ,
                                        :object_condition_qc2 
                            ) ON CONFLICT (continuous_sn_no) 
                            DO UPDATE 
                            SET 
                                uid = EXCLUDED.uid ,
                                album_no = EXCLUDED.album_no ,
                                object_condition_qc1 = EXCLUDED.object_condition_qc1 ,
                                album_information_old = EXCLUDED.album_information_old ,
                                album_information_new = EXCLUDED.album_information_new ,
                                photograph_information  = EXCLUDED.photograph_information ,
                                main_category  = EXCLUDED.main_category ,
                                collector_name = EXCLUDED.collector_name ,
                                day = EXCLUDED.day ,
                                month = EXCLUDED.month ,
                                year = EXCLUDED.year ,
                                country = EXCLUDED.country ,
                                locality = EXCLUDED.locality ,
                                gps_coordinates = EXCLUDED.gps_coordinates ,
                                taxonomy = EXCLUDED.taxonomy ,
                                common_name = EXCLUDED.common_name ,
                                fieldnotes = EXCLUDED.fieldnotes ,
                                keywords = EXCLUDED.keywords ,
                                location_in_lkcnhm = EXCLUDED.location_in_lkcnhm ,
                                catalogued_by = EXCLUDED.catalogued_by ,
                                catalogued_date = EXCLUDED.catalogued_date ,
                                access_status = EXCLUDED.access_status ,
                                remarks = EXCLUDED.remarks ,
                                negative_yn = EXCLUDED.negative_yn ,
                                batch_no = EXCLUDED.batch_no ,
                                sign_out_date = EXCLUDED.sign_out_date ,
                                sign_in_date = EXCLUDED.sign_in_date ,
                                date_of_qc = EXCLUDED.date_of_qc ,
                                checked_by = EXCLUDED.checked_by ,
                                object_condition_qc2 = EXCLUDED.object_condition_qc2
                            """
                    ),
                    df_raw.to_dicts(),
                )
            if is_futher_processing_disabled:
                return

        elif cols == negativeHeaders:
            # Raw Insertion
            df_raw = df.clone()
            df_raw.columns = [
                "sn_no",
                "uid",
                "ziplock_bag_no",
                "object_condition_qc1",
                "ziplock_bag_information",
                "negative_information",
                "main_category",
                "collector_name",
                "day",
                "month",
                "year",
                "country",
                "locality",
                "gps_coordinates",
                "taxonomy",
                "common_name",
                "fieldnotes",
                "keywords",
                "location_stored",
                "catalogued_by",
                "catalogued_date",
                "access_status",
                "remarks",
                "prints_yn",
                "batch_no",
                "sign_out_date",
                "sign_in_date",
                "date_of_qc",
                "checked_by",
                "object_condition_qc2",
            ]
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO negative_raw (
                            sn_no ,
                            uid ,
                            ziplock_bag_no ,
                            object_condition_qc1 ,
                            ziplock_bag_information ,
                            negative_information ,
                            main_category ,
                            collector_name ,
                            day ,
                            month ,
                            year ,
                            country ,
                            locality ,
                            gps_coordinates ,
                            taxonomy ,
                            common_name ,
                            fieldnotes ,
                            keywords ,
                            location_stored ,
                            catalogued_by ,
                           catalogued_date ,
                            access_status ,
                            remarks ,
                            prints_yn ,
                            batch_no ,
                            sign_out_date ,
                            sign_in_date ,
                            date_of_qc ,
                            checked_by ,
                            object_condition_qc2 
                        ) VALUES (
                            :sn_no ,
                            :uid ,
                            :ziplock_bag_no ,
                            :object_condition_qc1 ,
                            :ziplock_bag_information ,
                            :negative_information ,
                            :main_category ,
                            :collector_name ,
                            :day ,
                            :month ,
                            :year ,
                            :country ,
                            :locality ,
                            :gps_coordinates ,
                            :taxonomy ,
                            :common_name ,
                            :fieldnotes ,
                            :keywords ,
                            :location_stored ,
                            :catalogued_by ,
                            :catalogued_date ,
                            :access_status ,
                            :remarks ,
                            :prints_yn ,
                            :batch_no ,
                            :sign_out_date ,
                            :sign_in_date ,
                            :date_of_qc ,
                            :checked_by ,
                            :object_condition_qc2 
                            )
                        ON CONFLICT (sn_no) 
                        DO UPDATE 
                        SET
                            uid = EXCLUDED.uid ,
                            ziplock_bag_no = EXCLUDED.ziplock_bag_no ,
                            object_condition_qc1 = EXCLUDED.object_condition_qc1 ,
                            ziplock_bag_information = EXCLUDED.ziplock_bag_information ,
                            negative_information = EXCLUDED.negative_information ,
                            main_category = EXCLUDED.main_category ,
                            collector_name = EXCLUDED.collector_name ,
                            day = EXCLUDED.day ,
                            month = EXCLUDED.month ,
                            year = EXCLUDED.year ,
                            country = EXCLUDED.country ,
                            locality = EXCLUDED.locality ,
                            gps_coordinates = EXCLUDED.gps_coordinates ,
                            taxonomy = EXCLUDED.taxonomy ,
                            common_name = EXCLUDED.common_name ,
                            fieldnotes = EXCLUDED.fieldnotes ,
                            keywords = EXCLUDED.keywords ,
                            location_stored = EXCLUDED.location_stored ,
                            catalogued_by = EXCLUDED.catalogued_by ,
                            catalogued_date = EXCLUDED.catalogued_date ,
                            access_status = EXCLUDED.access_status ,
                            remarks = EXCLUDED.remarks ,
                            prints_yn = EXCLUDED.prints_yn ,
                            batch_no = EXCLUDED.batch_no ,
                            sign_out_date = EXCLUDED.sign_out_date ,
                            sign_in_date = EXCLUDED.sign_in_date ,
                            date_of_qc = EXCLUDED.date_of_qc ,
                            checked_by = EXCLUDED.checked_by ,
                            object_condition_qc2 = EXCLUDED.object_condition_qc2  
                            """
                    ),
                    df_raw.to_dicts(),
                )
                if is_futher_processing_disabled:
                    return
                # future futher processing logic here:
        elif cols == oralHistoryHeaders:
            df_raw = df.clone()
            df_raw.columns = [
                "sn",
                "name_of_interviewee",
                "name_of_interviewee_2",
                "recording_date_ddmmyyyy",
                "track_number",
                "total_tracks",
                "running_time",
                "file_name",
                "format_original_file",
                "access_conditions",
                "access_remarks",
                "transcription_status",
                "editing_remarks",
                "vetted_for_access",
                "accession_status",
                "languages",
                "keywords",
                "interview_location",
                "interviewers",
                "associated_materials",
                "catalogued_by",
                "catalogue_date",
                "comments",
            ]
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO oral_history_raw (
                                  sn ,
                                    name_of_interviewee ,
                                    name_of_interviewee_2 ,
                                    recording_date_ddmmyyyy ,
                                    track_number ,
                                    total_tracks ,
                                    running_time ,
                                    file_name ,
                                    format_original_file ,
                                    access_conditions ,
                                    access_remarks ,
                                    transcription_status ,
                                    editing_remarks ,
                                    vetted_for_access ,
                                    accession_status ,
                                    languages ,
                                    keywords ,
                                    interview_location ,
                                    interviewers ,
                                    associated_materials ,
                                    catalogued_by ,
                                    catalogue_date ,
                                    comments 
                        ) VALUES (
                                   :sn ,
                                    :name_of_interviewee ,
                                    :name_of_interviewee_2 ,
                                    :recording_date_ddmmyyyy ,
                                    :track_number ,
                                    :total_tracks ,
                                    :running_time ,
                                    :file_name ,
                                    :format_original_file ,
                                    :access_conditions ,
                                    :access_remarks ,
                                    :transcription_status ,
                                    :editing_remarks ,
                                    :vetted_for_access ,
                                    :accession_status ,
                                    :languages ,
                                    :keywords ,
                                    :interview_location ,
                                    :interviewers ,
                                    :associated_materials ,
                                    :catalogued_by ,
                                    :catalogue_date ,
                                    :comments 
                        ) ON CONFLICT (sn) 
                        DO UPDATE 
                        SET
                                    sn = EXCLUDED.sn ,
                                    name_of_interviewee = EXCLUDED.name_of_interviewee ,
                                    name_of_interviewee_2 = EXCLUDED.name_of_interviewee_2 ,
                                    recording_date_ddmmyyyy = EXCLUDED.recording_date_ddmmyyyy ,
                                    track_number = EXCLUDED.track_number ,
                                    total_tracks = EXCLUDED.total_tracks ,
                                    running_time = EXCLUDED.running_time ,
                                    file_name = EXCLUDED.file_name ,
                                    format_original_file = EXCLUDED.format_original_file ,
                                    access_conditions = EXCLUDED.access_conditions ,
                                    access_remarks = EXCLUDED.access_remarks ,
                                    transcription_status = EXCLUDED.transcription_status ,
                                    editing_remarks = EXCLUDED.editing_remarks ,
                                    vetted_for_access = EXCLUDED.vetted_for_access ,
                                    accession_status = EXCLUDED.accession_status ,
                                    languages = EXCLUDED.languages ,
                                    keywords = EXCLUDED.keywords ,
                                    interview_location = EXCLUDED.interview_location ,
                                    interviewers = EXCLUDED.interviewers ,
                                    associated_materials = EXCLUDED.associated_materials ,
                                    catalogued_by = EXCLUDED.catalogued_by ,
                                    catalogue_date = EXCLUDED.catalogue_date ,
                                    comments = EXCLUDED.comments 
                            """
                    ),
                    df_raw.to_dicts(),
                )
            if is_futher_processing_disabled:
                return

        elif cols == libraryAndArchiveHeader:
            df_raw = df.clone()
            df_raw.columns = [
                "sn",
                "category",
                "subcategory",
                "catalog_number",
                "object_status",
                "location_in_museum",
                "material_type",
                "subject",
                "shelving_location",
                "condition",
                "number_of_copies",
                "full_title",
                "journal_conference_report_workshop_name",
                "edition_number",
                "volume_number",
                "issue_number",
                "pages",
                "author",
                "from_year",
                "from_month",
                "from_date",
                "to_year",
                "to_month",
                "to_date",
                "isbnissn_number",
                "language",
                "country",
                "publisher",
                "organisation",
                "collection_name",
                "physical_description",
                "abstract",
                "keywords",
                "remarks",
                "recorded_by",
                "recorded_year",
                "scan_file_media",
                "transcription_file_media",
            ]
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO library_and_archive_raw (
                                sn ,
                                category ,
                                subcategory ,
                                catalog_number ,
                                object_status ,
                                location_in_museum ,
                                material_type ,
                                subject ,
                                shelving_location ,
                                condition ,
                                number_of_copies ,
                                full_title ,
                                journal_conference_report_workshop_name ,
                                edition_number ,
                                volume_number ,
                                issue_number ,
                                pages ,
                                author ,
                                from_year ,
                                from_month ,
                                from_date ,
                                to_year ,
                                to_month ,
                                to_date ,
                                isbnissn_number ,
                                language ,
                                country ,
                                publisher ,
                                organisation ,
                                collection_name ,
                                physical_description ,
                                abstract ,
                                keywords ,
                                remarks ,
                                recorded_by ,
                                recorded_year ,
                                scan_file_media ,
                                transcription_file_media  

                        ) VALUES (
                                :sn ,
                                :category ,
                                :subcategory ,
                                :catalog_number ,
                                :object_status ,
                                :location_in_museum ,
                                :material_type ,
                                :subject ,
                                :shelving_location ,
                                :condition ,
                                :number_of_copies ,
                                :full_title ,
                                :journal_conference_report_workshop_name ,
                                :edition_number ,
                                :volume_number ,
                                :issue_number ,
                                :pages ,
                                :author ,
                                :from_year ,
                                :from_month ,
                                :from_date ,
                                :to_year ,
                                :to_month ,
                                :to_date ,
                                :isbnissn_number ,
                                :language ,
                                :country ,
                                :publisher ,
                                :organisation ,
                                :collection_name ,
                                :physical_description ,
                                :abstract ,
                                :keywords ,
                                :remarks ,
                                :recorded_by ,
                                :recorded_year ,
                                :scan_file_media ,
                                :transcription_file_media  
                            ) ON CONFLICT (sn) 
                            DO UPDATE
                            SET
                                sn = EXCLUDED.sn ,
                                category = EXCLUDED.category ,
                                subcategory = EXCLUDED.subcategory ,
                                catalog_number = EXCLUDED.catalog_number ,
                                object_status = EXCLUDED.object_status ,
                                location_in_museum = EXCLUDED.location_in_museum ,
                                material_type = EXCLUDED.material_type ,
                                subject = EXCLUDED.subject ,
                                shelving_location = EXCLUDED.shelving_location ,
                                condition = EXCLUDED.condition ,
                                number_of_copies = EXCLUDED.number_of_copies ,
                                full_title = EXCLUDED.full_title ,
                                journal_conference_report_workshop_name = EXCLUDED.journal_conference_report_workshop_name ,
                                edition_number = EXCLUDED.edition_number ,
                                volume_number = EXCLUDED.volume_number ,
                                issue_number = EXCLUDED.issue_number ,
                                pages = EXCLUDED.pages ,
                                author = EXCLUDED.author ,
                                from_year = EXCLUDED.from_year ,
                                from_month = EXCLUDED.from_month ,
                                from_date = EXCLUDED.from_date ,
                                to_year = EXCLUDED.to_year ,
                                to_month = EXCLUDED.to_month ,
                                to_date = EXCLUDED.to_date ,
                                isbnissn_number = EXCLUDED.isbnissn_number ,
                                language = EXCLUDED.language ,
                                country = EXCLUDED.country ,
                                publisher = EXCLUDED.publisher ,
                                organisation = EXCLUDED.organisation ,
                                collection_name = EXCLUDED.collection_name ,
                                physical_description = EXCLUDED.physical_description ,
                                abstract = EXCLUDED.abstract ,
                                keywords = EXCLUDED.keywords ,
                                remarks = EXCLUDED.remarks ,
                                recorded_by = EXCLUDED.recorded_by ,
                                recorded_year = EXCLUDED.recorded_year ,
                                scan_file_media = EXCLUDED.scan_file_media ,
                                transcription_file_media = EXCLUDED.transcription_file_media 

                            """
                    ),
                    df_raw.to_dicts(),
                )
            if is_futher_processing_disabled:
                return
        elif cols == slideHeaders:
            df_raw = df.clone()
            df_raw.columns = [
                "sn_no",
                "uid",
                "box_no",
                "object_condition_qc1",
                "box_information_old",
                "box_information_new",
                "divider_1",
                "divider_2",
                "divider_3",
                "slides_information",
                "main_category",
                "collector_name",
                "day",
                "month",
                "year",
                "country",
                "locality",
                "gps_coordinates",
                "taxonomy",
                "common_name",
                "fieldnotes",
                "keywords",
                "location_in_lkcnhm",
                "catalogued_by",
                "catalogued_date",
                "access_status",
                "remarks",
                "batch_no",
                "sign_out_date",
                "sign_in_date",
                "date_of_qc",
                "checked_by",
                "object_condition_qc2",
                "data_tier_2_or_3",
            ]
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO slide_raw (
                                    sn_no ,
                                    uid ,
                                    box_no ,
                                    object_condition_qc1 ,
                                    box_information_old ,
                                    box_information_new ,
                                    divider_1 ,
                                    divider_2 ,
                                    divider_3 ,
                                    slides_information ,
                                    main_category ,
                                    collector_name ,
                                    day ,
                                    month ,
                                    year ,
                                    country ,
                                    locality ,
                                    gps_coordinates ,
                                    taxonomy ,
                                    common_name ,
                                    fieldnotes ,
                                    keywords ,
                                    location_in_lkcnhm ,
                                    catalogued_by ,
                                   catalogued_date ,
                                    access_status ,
                                    remarks ,
                                    batch_no ,
                                    sign_out_date ,
                                    sign_in_date ,
                                    date_of_qc ,
                                    checked_by ,
                                    object_condition_qc2 ,
                                    data_tier_2_or_3 

                        ) VALUES (
                                    :sn_no ,
                                    :uid ,
                                    :box_no ,
                                    :object_condition_qc1 ,
                                    :box_information_old ,
                                    :box_information_new ,
                                    :divider_1 ,
                                    :divider_2 ,
                                    :divider_3 ,
                                    :slides_information ,
                                    :main_category ,
                                    :collector_name ,
                                    :day ,
                                    :month ,
                                    :year ,
                                    :country ,
                                    :locality ,
                                    :gps_coordinates ,
                                    :taxonomy ,
                                    :common_name ,
                                    :fieldnotes ,
                                    :keywords ,
                                    :location_in_lkcnhm ,
                                    :catalogued_by ,
                                    :catalogued_date ,
                                    :access_status ,
                                    :remarks ,
                                    :batch_no ,
                                    :sign_out_date ,
                                    :sign_in_date ,
                                    :date_of_qc ,
                                    :checked_by ,
                                    :object_condition_qc2 ,
                                    :data_tier_2_or_3 
                            )ON CONFLICT (sn_no) 
                            DO UPDATE
                            SET
                                    uid = EXCLUDED.uid ,
                                    box_no = EXCLUDED.box_no ,
                                    object_condition_qc1 = EXCLUDED.object_condition_qc1 ,
                                    box_information_old = EXCLUDED.box_information_old ,
                                    box_information_new = EXCLUDED.box_information_new ,
                                    divider_1 = EXCLUDED.divider_1 ,
                                    divider_2 = EXCLUDED.divider_2 ,
                                    divider_3 = EXCLUDED.divider_3 ,
                                    slides_information = EXCLUDED.slides_information ,
                                    main_category = EXCLUDED.main_category ,
                                    collector_name = EXCLUDED.collector_name ,
                                    day = EXCLUDED.day ,
                                    month = EXCLUDED.month ,
                                    year = EXCLUDED.year ,
                                    country = EXCLUDED.country ,
                                    locality = EXCLUDED.locality ,
                                    gps_coordinates = EXCLUDED.gps_coordinates ,
                                    taxonomy = EXCLUDED.taxonomy ,
                                    common_name = EXCLUDED.common_name ,
                                    fieldnotes = EXCLUDED.fieldnotes ,
                                    keywords = EXCLUDED.keywords ,
                                    location_in_lkcnhm = EXCLUDED.location_in_lkcnhm ,
                                    catalogued_by = EXCLUDED.catalogued_by ,
                                   catalogued_date = EXCLUDED.catalogued_date ,
                                    access_status = EXCLUDED.access_status ,
                                    remarks = EXCLUDED.remarks ,
                                    batch_no = EXCLUDED.batch_no ,
                                    sign_out_date = EXCLUDED.sign_out_date ,
                                    sign_in_date = EXCLUDED.sign_in_date ,
                                    date_of_qc = EXCLUDED.date_of_qc ,
                                    checked_by = EXCLUDED.checked_by ,
                                    object_condition_qc2 = EXCLUDED.object_condition_qc2 ,
                                    data_tier_2_or_3 = EXCLUDED.data_tier_2_or_3  
                            """
                    ),
                    df_raw.to_dicts(),
                )
            if is_futher_processing_disabled:
                return
        else:
            raise HTTPException(
                status_code=422, detail="unable to decipher the catalog type"
            )

        results = []
        results.append({"filename": file.filename})
    return {"uploaded_files": results}


@router.post("/deleteSelectedRows")
async def delete_selected_rows(model_instance: DeleteSelectedRowsModel):
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
        DELETE FROM {literal_column(model_instance.catalogue_name)}_raw 
        WHERE {literal_column(model_instance.catalogue_name)}_raw_id IN :ids_to_be_deleted
        """,
            )
            .bindparams(
                bindparam(
                    key="ids_to_be_deleted",
                    value=model_instance.ids_to_be_deleted,
                    expanding=True,
                )
            )
            .compile(compile_kwargs={"literal_binds": True}),
        )
    return {"ok": True, "message": "deleted selected rows"}


@router.post("/downloadFiles")
async def download_files(
    conditions: DownloadFilesModel,
):
    if conditions.selected_catalogues == []:
        raise HTTPException(422, "Missing selected catalogue names.")
    results = []
    for catalogue_name in conditions.selected_catalogues:
        sql = f"""
                SELECT * FROM {literal_column(catalogue_name)}_raw
                    """
        where_sql_condition = ""
        where_sql_date_range_condition = ""
        search_term = conditions.search_term
        # date_range = conditions.date_range
        # start_date = ""
        # end_date = ""
        # years = []
        params = {}
        if search_term != "":
            for i, x in enumerate(get_header_dict[catalogue_name]):
                keyword = "WHERE" if i == 0 else "OR"
                where_sql_condition += (
                    f" {keyword} {literal_column(x)} ILIKE :search_term{i}"
                )
            for x in range(len(get_header_dict[catalogue_name])):
                params[f"search_term{x}"] = "%" + search_term + "%"

        # if len(date_range) != 0:
        #     print("date_range", date_range)

        #     if catalogue_name == "library_and_archive":
        #         where_sql_date_range_condition = "recorded_year IN ARRAY(:years)"

        #     else:
        #         start_date = date_range[0]
        #         end_date = date_range[1]
        #         print("start_date", start_date)
        #         print("end_date", end_date)
        #         where_sql_date_range_condition = (
        #             "catalogued_date BETWEEN :start_date AND :end_date"
        #         )

        #     where_sql_date_range_condition = (
        #         "WHERE " + where_sql_date_range_condition
        #         if search_term == ""
        #         else "AND" + where_sql_date_range_condition
        #     )
        #     print("where_sql_date_range_condition", where_sql_date_range_condition)

        with engine.begin() as connection:
            result = connection.execute(
                text(sql + where_sql_condition + where_sql_date_range_condition),
                [params],
            ).all()

            results.append(
                {
                    "catalogue_name": catalogue_name,
                    "data": [x._asdict() for x in result],
                }
            )
    # print(results)
    return {"message": "success", "results": results}


def old_transformation_for_print(df, user_id):

    # Location in LKCNHM
    # fields not inserted yet:

    #   associated_negative_id ,
    # taxonomy
    # common name
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

    # Get unique values for various tables to be inserted if they do not exist. And to turn them into id as reflected in the db for foreign keys field during insertions
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
                "album_information_old": row["album_information_old"].replace('"', ""),
                "album_information_new": row["album_information_new"]
                .replace('"', "")
                .replace("/", ""),
            }
        )
        for row in params_dict
    ]
    df_params = pl.concat(
        [df_params, pl.DataFrame(album_json, schema={"album": pl.String})],
        how="horizontal",
    )
    try:
        with engine.begin() as connection:
            # Collectors and catalogurs ---------------------------------------------

            for name in unique_collectors_names:
                insert_into_person_if_not_exist_in_name_held(name, user_id, connection)

            for name in unique_sets_of_cataloguer_names:
                insert_into_person_if_not_exist_in_name_held(name, user_id, connection)

            # Get all people including collectors just added.
            people = get_all_people_from_person_table(connection)

            # change the collector_name into collector-id in params_dict and catagoluers_name into cataloger_ids in params_dict
            df_params = df_params_sorting_of_names_and_ids(
                df_params, people, "collector", "name_held", "person"
            )

            df_params = df_params_sorting_of_names_and_id_in_list_fields(
                df_params, people, "catalogued_by", "name_held", "person_id"
            )

            # Locality --------------------------------------------------------
            # insert any new country locality into locality table
            for locality in unique_country_names:
                result = find_if_locality_name_exists_in_db(locality, connection)
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
                result = find_if_locality_name_exists_in_db(locality[0], connection)
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
                result = find_if_locality_name_exists_in_db(locality, connection)
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
            formatted_error_message = "You have uploaded rows with non unique s/n"
        else:
            formatted_error_message = error_string
        raise HTTPException(
            status_code=422,
            detail=formatted_error_message,
        )


def old_transformation_for_oral_history(
    df,
    user_id,
):
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
        interviewer_names=pl.col("interviewer_names").str.strip_chars().str.split(","),
        interviewee_names=pl.concat_list(
            "name_of_interviewee1", "name_of_interviewee2"
        ),
    )

    # Get unique values for various tables to be inserted if they do not exist. And to turn them into id as reflected in the db for foreign keys field during insertions
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
                insert_into_person_if_not_exist_in_name_held(name, user_id, connection)
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
                results = find_if_locality_name_exists_in_db(locality, connection)
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
                pl.col("track_duration").str.split(" ").list[1].alias("track_duration")
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
    except IntegrityError as e:
        pass


@router.get("/DownloadTemplatesForTheCatelogs")
def download_templates_for_the_catelogs():
    file_path = "./templates for the catelogs.zip"
    return FileResponse(file_path, media_type="application/zip")
