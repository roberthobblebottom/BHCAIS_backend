import json  # noqa: I001
from typing import Annotated
import polars as pl
from fastapi import APIRouter, File, HTTPException, UploadFile, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import literal_column, bindparam
from src.db.db_wrapper import engine, text
from src.auth.jwthandler import route_auth_by_token, admin_route_auth_by_token
from ..constants import (
    get_header_dict,
    legacy_and_miscellaneous_items_report_sql_string_columns,
    library_and_archives_sql_string_columns,
    print_sql_string_columns,
    oral_histories_sql_string_columns,
    negative_sql_string_columns,
    slides_sql_string_columns,
)
from fastapi.responses import FileResponse
from src.Models import DeleteSelectedRowsModel, DownloadFilesModel

router = APIRouter()


@router.get("/GetCatalogue", status_code=200)
async def get_catalogue(
    catalogue_name: str,
    rows_per_page: int,
    current_page_number: int,
    filter_str: str,
    sort_by: str,
    descending: bool,
    token: str = Depends(route_auth_by_token),
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
            f"""ORDER BY {literal_column(sort_by)}
            """
            if sort_by not in ["desc", "null", ""]
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
        params = {
            "sort_by": sort_by,
            "fetch_count": fetchCount,
            "start_row": startRow,
        }
        if filter_str != "":
            for x in range(len(get_header_dict[catalogue_name])):
                params[f"filter_str{x}"] = filter_str
        results = [
            row._asdict()
            for row in connection.execute(
                text(sql),
                [params],
            ).all()
        ]
        return {"results": results, "row_counts": row_counts}


async def _upsert_into_db(file: File):
    contents = await file.read()

    # Checking of validity of the files::w

    if ".xlsx" in file.filename:
        df = pl.read_excel(contents, infer_schema_length=0)
    elif ".csv" in file.filename:
        df = pl.read_csv(contents, infer_schema_length=0, ignore_errors=True)
        while "" in df.columns:
            df = df.drop("")
    else:
        raise HTTPException(
            status_code=422,
            details="The file " + file.filename + " is not in .csv or .xlsx",
        )

    df = df.with_columns(pl.all().cast(pl.String, strict=True)).with_columns(
        # pl.all().str.replace_all('"', "'", literal=True)
    )
    if df.shape[0] <= 1:
        raise HTTPException(
            status_code=422,
            detail="The file "
            + file.filename
            + " is either empty or only contains header",
        )
    cols = [col.lower().strip() for col in df.columns if col != ""]

    if (
        cols != print_sql_string_columns
        and cols != oral_histories_sql_string_columns
        and cols != slides_sql_string_columns
        and cols != negative_sql_string_columns
        and cols != library_and_archives_sql_string_columns
        and cols != legacy_and_miscellaneous_items_report_sql_string_columns
    ):
        return

    ### Individual Catalogue processing
    if cols == print_sql_string_columns:
        # Raw Insertion
        df_raw = df.clone()

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
    elif cols == negative_sql_string_columns:
        # Raw Insertion
        df_raw = df.clone()
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
            # future futher processing logic here:
    elif cols == oral_histories_sql_string_columns:
        df_raw = df.clone()

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
    elif cols == library_and_archives_sql_string_columns:
        df_raw = df.clone()

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
    elif cols == slides_sql_string_columns:
        df_raw = df.clone()
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
    elif cols == legacy_and_miscellaneous_items_report_sql_string_columns:
        df_raw = df.clone()
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                        INSERT INTO legacy_and_miscellaneous_items_report_raw (
                                      sn,
                                        category,
                                        catalog_number,
                                        subcategory,
                                        object_status,
                                        name,
                                        asset_number,
                                        type_status,
                                        individual_count,
                                        preservation,
                                        preservation_description_of_components,
                                        location_in_museum,
                                        sex,
                                        treatment,
                                        use_ethnographical_significance,
                                        material,
                                        condition,
                                        dimensions,
                                        higher_classification,
                                        family,
                                        genus,
                                        subgenus,
                                        species,
                                        subspecies,
                                        scientific_name_author,
                                        scientific_name_author_year,
                                        common_name,
                                        country_ocean,
                                        locality,
                                        acquisition,
                                        collected_by,
                                        verbatim_date,
                                        from_day,
                                        from_month,
                                        from_year,
                                        to_day,
                                        to_month,
                                        to_year,
                                        relative_humidity_for_storage_display,
                                        temperature_celcius,
                                        lux_light_levels,
                                        remarks,
                                        title,
                                        web_url,
                                        nas_link
                                        ) VALUES (
                                            :sn,
                                            :category,
                                            :catalog_number,
                                            :subcategory,
                                            :object_status,
                                            :name,
                                            :asset_number,
                                            :type_status,
                                            :individual_count,
                                            :preservation,
                                            :preservation_description_of_components,
                                            :location_in_museum,
                                            :sex,
                                            :treatment,
                                            :use_ethnographical_significance,
                                            :material,
                                            :condition,
                                            :dimensions,
                                            :higher_classification,
                                            :family,
                                            :genus,
                                            :subgenus,
                                            :species,
                                            :subspecies,
                                            :scientific_name_author,
                                            :scientific_name_author_year,
                                            :common_name,
                                            :country_ocean,
                                            :locality,
                                            :acquisition,
                                            :collected_by,
                                            :verbatim_date,
                                            :from_day,
                                            :from_month,
                                            :from_year,
                                            :to_day,
                                            :to_month,
                                            :to_year,
                                            :relative_humidity_for_storage_display,
                                            :temperature_celcius,
                                            :lux_light_levels,
                                            :remarks,
                                            :title,
                                            :web_url,
                                            :nas_link
                                      
                                   
                            )ON CONFLICT (sn) 
                            DO UPDATE
                            SET
                                category    = EXCLUDED.category,
                                catalog_number   = EXCLUDED.catalog_number,
                                subcategory   = EXCLUDED.subcategory,
                                object_status  = EXCLUDED.object_status,
                                name = EXCLUDED.name,
                                asset_number    = EXCLUDED.asset_number,
                                type_status  = EXCLUDED.type_status,
                                individual_count   = EXCLUDED.individual_count,
                                preservation  = EXCLUDED.preservation,
                                preservation_description_of_components  = EXCLUDED.preservation_description_of_components,
                                location_in_museum  = EXCLUDED.location_in_museum,
                                sex  = EXCLUDED.sex,
                                treatment  = EXCLUDED.treatment,
                                use_ethnographical_significance   = EXCLUDED.use_ethnographical_significance,
                                material  = EXCLUDED.material,
                                condition  = EXCLUDED.condition,
                                dimensions = EXCLUDED.dimensions,
                                higher_classification  = EXCLUDED.higher_classification,
                                family = EXCLUDED.family,
                                genus = EXCLUDED.genus,
                                subgenus = EXCLUDED.subgenus,
                                species = EXCLUDED.species,
                                subspecies  = EXCLUDED.subspecies,
                                scientific_name_author  = EXCLUDED.scientific_name_author,
                                scientific_name_author_year  = EXCLUDED.scientific_name_author_year,
                                common_name = EXCLUDED.common_name,
                                country_ocean = EXCLUDED.country_ocean,
                                locality = EXCLUDED.locality,
                                acquisition = EXCLUDED.acquisition,
                                collected_by = EXCLUDED.collected_by,
                                verbatim_date  = EXCLUDED.verbatim_date,
                                from_day    = EXCLUDED.from_day,
                                from_month    = EXCLUDED.from_month,
                                from_year   = EXCLUDED.from_year,
                                to_day   = EXCLUDED.to_day,
                                to_month    = EXCLUDED.to_month,
                                to_year  = EXCLUDED.to_year,
                                relative_humidity_for_storage_display  = EXCLUDED.relative_humidity_for_storage_display,
                                temperature_celcius  = EXCLUDED.temperature_celcius,
                                lux_light_levels  = EXCLUDED.lux_light_levels,
                                remarks = EXCLUDED.remarks,
                                title  = EXCLUDED.title,
                                web_url  = EXCLUDED.web_url,
                                nas_link = EXCLUDED.nas_link
                            """
                ),
                df_raw.to_dicts(),
            )

    else:
        raise HTTPException(
            status_code=422, detail="unable to decipher the catalog type"
        )

    results = []
    results.append({"filename": file.filename})


@router.post("/UploadFiles")
async def upload_files(
    files: Annotated[list[UploadFile], File()],
    user_id: int,
    token: str,
    background_tasks: BackgroundTasks = None,
):
    route_auth_by_token(token)
    results = []
    for file in files:
        print("pre check", file.filename)
        background_tasks.add_task(_upsert_into_db, file)

    return {"uploaded_files": results}


@router.delete("/DeleteSelectedRows")
async def delete_selected_rows(
    model_instance: DeleteSelectedRowsModel,
):

    Depends(route_auth_by_token(model_instance.token))

    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
        DELETE FROM {literal_column(model_instance.catalogue_name)}_raw 
        WHERE {literal_column(model_instance.current_primary_key)} 
        IN :ids_to_be_deleted
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


@router.delete("/DeleteAllCatalogueData")
async def delete_all_catalogue_data(token: str):
    Depends(admin_route_auth_by_token(token))
    with engine.begin() as connection:
        connection.execute(
            text("""DELETE FROM print_raw;
                    DELETE FROM oral_history_raw;
                    DELETE FROM negative_raw;
                    DELETE FROM slide_raw;
                    DELETE FROM library_and_archive_raw;
                    DELETE FROM legacy_and_miscellaneous_items_report_raw; 
    """)
        )
    return {"ok": True, "message": "deleted all catalogue data"}


@router.post("/DownloadFiles", response_class=StreamingResponse)
async def download_files(
    conditions: DownloadFilesModel,
):
    Depends(route_auth_by_token(token=conditions.token))
    if conditions.selected_catalogues == []:
        raise HTTPException(422, "Missing selected catalogue names.")
    for catalogue_name in conditions.selected_catalogues:
        sql = f"""SELECT * FROM {literal_column(catalogue_name)}_raw"""
        where_condition = ""
        where_sql_date_range_condition = ""
        search_terms = conditions.search_terms
        params = {}
        if len(search_terms.keys()) != 0 and catalogue_name in search_terms:
            for i, x in enumerate(search_terms[catalogue_name].items()):
                keyword = (
                    "WHERE" if i == 0 else "AND"
                )  # Using OR returns too much back.
                where_condition += (
                    f" {keyword} {literal_column(x[0])} ILIKE :search_term{i}"
                )
                params[f"search_term{i}"] = "%" + x[1] + "%"

        with engine.begin() as connection:
            result = connection.execute(
                text(sql + where_condition + where_sql_date_range_condition),
                [params],
            ).all()

            yield "catalogue_name=" + catalogue_name
            if len(result) > 0:
                for i, x in enumerate(result):
                    yield json.dumps(x._asdict()) + ","
            else:
                yield " no results"


# def old_transformation_for_print(df, user_id):

#     # Location in LKCNHM
#     # fields not inserted yet:

#     #   associated_negative_id ,
#     # taxonomy
#     # common name
#     df_params = df.select(
#         "UID",
#         "Album no.",
#         "Object Condition (QC1)",
#         "Album Information (OLD)",
#         "Album Information (New)",
#         "Photograph Information",
#         "Main Category",
#         "Collector's Name",
#         "Day",
#         "Month",
#         "Year",
#         "Country",
#         "Locality",
#         "GPS Coordinates",
#         "Fieldnotes",
#         "Keywords",
#         "Location in LKCNHM",
#         "Catalogued by",
#         "Date catalogued",
#         "Access status",
#         "Remarks",
#         "Batch no.",
#     ).with_columns(
#         uploaded_by_user_of_id=pl.lit(int(user_id)),
#         upload_date=pl.lit("NOW()"),
#     )
#     df_params.columns = [
#         "uid",
#         "album_number",
#         "object_condition",
#         "album_information_old",
#         "album_information_new",
#         "photograph_label_info",
#         "main_category",
#         "collector_name",
#         "taken_day",
#         "taken_month",
#         "taken_year",
#         "country",
#         "locality",
#         "gps_coordinates",
#         "fieldnotes",
#         "keywords",
#         "repository_location_id",
#         "catalogued_by_names",
#         "dates_catalogued",
#         "access_level",
#         "remarks",
#         "batch_number",
#         "uploaded_by_user_of_id",
#         "upload_date",
#     ]  # renaming
#     df_params = df_params.with_columns(
#         pl.col("dates_catalogued").str.strip_chars().str.split("||"),
#         pl.col("catalogued_by_names").str.strip_chars().str.split("||"),
#     )

#     # Get unique values for various tables to be inserted if they do not exist. And to turn them into id as reflected in the db for foreign keys field during insertions
#     unique_collectors_names = df_params["collector_name"].unique().to_list()
#     unique_sets_of_cataloguer_names = (
#         df_params["catalogued_by_names"].unique().to_list()
#     )
#     unique_country_names = df_params["country"].unique().to_list()
#     unique_localities = (
#         df_params["locality", "country", "gps_coordinates"]
#         .filter(~pl.col("locality").str.to_lowercase().is_in(["nil", "na"]))
#         .unique()
#     )
#     unique_repository_location_ids = (
#         df_params["repository_location_id"].unique().to_list()
#     )
#     params_dict = df_params.to_dicts()
#     album_json = [
#         json.dumps(
#             {
#                 "album_number": row["album_number"],
#                 "album_information_old": row["album_information_old"].replace('"', ""),
#                 "album_information_new": row["album_information_new"]
#                 .replace('"', "")
#                 .replace("/", ""),
#             }
#         )
#         for row in params_dict
#     ]
#     df_params = pl.concat(
#         [df_params, pl.DataFrame(album_json, schema={"album": pl.String})],
#         how="horizontal",
#     )
#     try:
#         with engine.begin() as connection:
#             # Collectors and catalogurs ---------------------------------------------

#             for name in unique_collectors_names:
#                 insert_into_person_if_not_exist_in_name_held(name, user_id, connection)

#             for name in unique_sets_of_cataloguer_names:
#                 insert_into_person_if_not_exist_in_name_held(name, user_id, connection)

#             # Get all people including collectors just added.
#             people = get_all_people_from_person_table(connection)

#             # change the collector_name into collector-id in params_dict and catagoluers_name into cataloger_ids in params_dict
#             df_params = df_params_sorting_of_names_and_ids(
#                 df_params, people, "collector", "name_held", "person"
#             )

#             df_params = df_params_sorting_of_names_and_id_in_list_fields(
#                 df_params, people, "catalogued_by", "name_held", "person_id"
#             )

#             # Locality --------------------------------------------------------
#             # insert any new country locality into locality table
#             for locality in unique_country_names:
#                 result = find_if_locality_name_exists_in_db(locality, connection)
#                 if result is None:
#                     insert_into_locality(
#                         {
#                             "locality_name": locality,
#                             "locality_rank": "country",
#                             "parent_locality": None,
#                             "uploaded_by_user_of_id": user_id,
#                             "upload_date": "NOW()",
#                         },
#                         connection,
#                     )

#             # Get all countries even the one that are just added
#             countries = get_unique_localities(
#                 where="WHERE locality_rank = 'country'", connection=connection
#             )
#             # countries = [[locality id, locality name]] USE INDICES
#             # insert any new locality  into the locality table
#             for locality in (
#                 unique_localities.iter_rows()
#             ):  # [locality (place name), country, gps coords ] USE INDICES
#                 result = find_if_locality_name_exists_in_db(locality[0], connection)
#                 if result is None:
#                     # get all country id in roles for specific locations insertion entries to be inserted right below
#                     country_id = -1
#                     for c in countries:
#                         if (
#                             c[1] == locality[1]
#                         ):  # locality_name on both side of the equation
#                             country_id = c[0]
#                         ###############################
#                         (
#                             insert_into_locality(
#                                 {
#                                     "locality_name": locality[0],
#                                     "locality_rank": "place",
#                                     "parent_locality": country_id,
#                                     "uploaded_by_user_of_id": user_id,
#                                     "upload_date": "NOW()",
#                                 },
#                                 connection,
#                             ),
#                         )

#             # insert any new repository locations
#             for locality in unique_repository_location_ids:
#                 result = find_if_locality_name_exists_in_db(locality, connection)
#                 if result is None:
#                     insert_into_locality(
#                         {
#                             "locality_name": locality,
#                             "locality_rank": "repository location",
#                             "parent_locality": 2,  # For NUS
#                             "uploaded_by_user_of_id": user_id,
#                             "upload_date": "NOW()",
#                         },
#                         connection,
#                     )

#             # get all localities including the ones just added
#             unique_localities = get_unique_localities(connection=connection)
#             unique_localities = pl.DataFrame(
#                 unique_localities, schema=["locality_id", "locality_name"]
#             )

#             # change locality name to locality id for "locality" and "repository_locality" in params_dict
#             df_params = localities_params_dict_sorting_of_names_and_ids(
#                 df_params, unique_localities, "locality"
#             )
#             df_params = localities_params_dict_sorting_of_names_and_ids(
#                 df_params,
#                 unique_localities,
#                 "repository_location_id",
#             )
#             params_dict = df_params.to_dicts()
#             print(params_dict[0])
#             # Main insertion into print table
#             connection.execute(
#                 text(
#                     """INSERT INTO print (
#                         uid  ,
#                         object_condition,
#                         photograph_label_info ,
#                         main_category,
#                         taken_day ,
#                         taken_month ,
#                         taken_year ,
#                         taken_locality_id,
#                         fieldnotes ,
#                         keywords,

#                         repository_location_id,
#                         access_level,
#                         remarks ,
#                         batch_number ,
#                         uploaded_by_user_of_id ,
#                         upload_date,
#                         catalogued_by_ids,
#                         dates_catalogued ,
#                         album,
#                         collector_id
#                     )
#                 VALUES
#                     (
#                         :uid  ,
#                     :object_condition,
#                     :photograph_label_info ,
#                     :main_category,
#                     :taken_day ,
#                     :taken_month ,
#                     :taken_year ,
#                     :locality,
#                     :fieldnotes ,
#                     :keywords,
#                     :repository_location_id,
#                     :access_level,
#                     :remarks ,
#                     :batch_number ,
#                     :uploaded_by_user_of_id ,
#                     :upload_date,

#                     :catalogued_by_ids,
#                     :dates_catalogued ,
#                     :album,
#                     :collector_id
#                     ) """
#                 ),
#                 params_dict,
#             )

#     except IntegrityError as e:
#         error_string = str(e)
#         formatted_error_message = ""
#         if "UniqueViolation" in error_string:
#             formatted_error_message = "You have uploaded rows with non unique s/n"
#         else:
#             formatted_error_message = error_string
#         raise HTTPException(
#             status_code=422,
#             detail=formatted_error_message,
#         )


# def old_transformation_for_oral_history(
#     df,
#     user_id,
# ):
#     df_params = df.select(
#         "S/N",
#         "Name of Interviewee",
#         "Name of Interviewee (2)",
#         "Recording Date (DD/MM/YYYY)",
#         "Track Number",
#         "Total Tracks",
#         "Running Time",
#         "File name",
#         "Format (Original File)",
#         "Access Conditions",
#         "Access Remarks",
#         "Transcription Status",
#         "Editing Remarks",
#         "Vetted for Access?",
#         "Accession Status",
#         "Languages",
#         "Keywords",
#         "Interview Location",
#         "Interviewers",
#         "Associated Materials",
#         "Catalogued By",
#         "Catalogue Date",
#         "Comments",
#     ).with_columns(
#         uploaded_by_user_of_id=pl.lit(int(user_id)),
#         upload_date=pl.lit("NOW()"),
#     )
#     df_params.columns = [
#         "sn",
#         "name_of_interviewee1",
#         "name_of_interviewee2",
#         "recording_date",
#         "track_number",
#         "total_tracks",
#         "track_duration",
#         "file_name",
#         "file_format",
#         "access_condition",
#         "access_remarks",
#         "transcription_status",
#         "track_editing_remarks",
#         "was_vetted_for_access",
#         "accession_status",
#         "primary_language",
#         "keywords",
#         "interview_location_name",
#         "interviewer_names",
#         "associated_materials",
#         "catalogued_by",
#         "catalogued_date",
#         "comments",
#         "uploaded_by_user_of_id",
#         "upload_date",
#     ]  # renaming

#     df_params = df_params.with_columns(
#         interviewer_names=pl.col("interviewer_names").str.strip_chars().str.split(","),
#         interviewee_names=pl.concat_list(
#             "name_of_interviewee1", "name_of_interviewee2"
#         ),
#     )

#     # Get unique values for various tables to be inserted if they do not exist. And to turn them into id as reflected in the db for foreign keys field during insertions
#     unique_interview_participant_names = (
#         df_params["interviewer_names"].explode().unique().to_list()
#         + df_params["interviewee_names"].explode().unique().to_list()
#     )
#     unique_interview_participant_names = [
#         x for x in unique_interview_participant_names if x is not None
#     ]
#     unique_localities = (
#         df_params.filter(pl.col("interview_location_name").is_not_null())[
#             "interview_location_name"
#         ]
#         .unique()
#         .to_list()
#     )
#     try:
#         with engine.begin() as connection:
#             # Insert new interviewers if it does not exist
#             for name in unique_interview_participant_names:
#                 insert_into_person_if_not_exist_in_name_held(name, user_id, connection)
#             people = get_all_people_from_person_table(connection)
#             df_params = df_params.with_columns()
#             df_params = df_params_sorting_of_names_and_id_in_list_fields(
#                 df_params, people, "interviewee", "name_held", "person_id"
#             )
#             df_params = df_params_sorting_of_names_and_id_in_list_fields(
#                 df_params, people, "interviewer", "name_held", "person_id"
#             )
#             # locality
#             for locality in unique_localities:
#                 results = find_if_locality_name_exists_in_db(locality, connection)
#                 if results is None:
#                     insert_into_locality(
#                         {
#                             "locality_name": locality,
#                             "locality_rank": "place",
#                             "parent_locality": None,
#                             "uploaded_by_user_of_id": user_id,
#                             "upload_date": "NOW()",
#                         },
#                         connection,
#                     )

#             unique_localities = pl.DataFrame(
#                 get_unique_localities(where=None, connection=connection),
#             )

#             # change locality name to locality id for "locality" and "repository_locality" in params_dict
#             df_params = df_params_sorting_of_names_and_ids(
#                 df_params,
#                 unique_localities,
#                 "interview_location",
#                 "locality_name",
#                 "locality",
#             )
#             df_grouped = df_params.with_columns(
#                 pl.col("track_duration").str.split(" ").list[1].alias("track_duration")
#             ).group_by(["interviewer_ids", "interviewee_ids", "total_tracks"])
#             df_grouped = (
#                 df_grouped.agg(
#                     "file_name",
#                     "recording_date",
#                     "track_duration",
#                     "access_condition",
#                     "access_remarks",
#                     "primary_language",
#                     "interview_location_id",
#                     "comments",
#                 )
#                 .with_columns(
#                     uploaded_by_user_of_id=pl.lit(int(user_id)),
#                     upload_date=pl.lit("NOW()"),
#                 )
#                 .with_columns(
#                     pl.col(pl.List(pl.String())).list.agg(
#                         pl.element().drop_nulls().drop_nans().unique()
#                     ),
#                     pl.col(pl.List(pl.Int64())).list.agg(
#                         pl.element().drop_nans().drop_nulls().unique()
#                     ),
#                     pl.col(pl.List(pl.Int16())).list.agg(
#                         pl.element().drop_nans().drop_nulls().unique()
#                     ),
#                 )
#                 .with_columns(
#                     pl.col(
#                         "track_duration",
#                         "recording_date",
#                         "file_name",
#                         "access_condition",
#                         "access_condition",
#                         "access_remarks",
#                         "primary_language",
#                         "comments",
#                     ).list.join(","),
#                     ### this block for interview_location_id must be done twice or else out of bounce error will occur:
#                     pl.when(
#                         (pl.col("interview_location_id").list.len() == 0)
#                         | (pl.col("interview_location_id").is_null())
#                     )
#                     .then(pl.lit(None))
#                     .otherwise("interview_location_id")
#                     .alias("interview_location_id"),
#                 )
#             )

#             df_grouped = df_grouped.with_columns(
#                 pl.when(pl.col("primary_language") == "")
#                 .then(pl.lit("NULL"))
#                 .otherwise("primary_language")
#                 .alias("primary_language"),
#                 pl.when(pl.col("interviewer_ids").list.len() == 0)
#                 .then(pl.lit(None))
#                 .otherwise("interviewer_ids")
#                 .alias("interviewer_ids"),
#                 pl.when(pl.col("interviewee_ids").list.len() == 0)
#                 .then(pl.lit(None))
#                 .otherwise("interviewee_ids")
#                 .alias("interviewee_ids"),
#                 ### this block for interview_location_id must be done twice or else out of bounce error will occur:
#                 pl.when(
#                     (pl.col("interview_location_id").list.len() == 0)
#                     | (pl.col("interview_location_id").is_null())
#                 )
#                 .then(pl.lit(None))
#                 .otherwise(
#                     pl.col("interview_location_id").list[0]
#                 )  # GET THE FIRST INTERVIEW LOCATION ID
#                 .alias("interview_location_id"),
#             )

#             # retur
#             # Main insertion into Oral table table
#             connection.execute(
#                 text(
#                     """INSERT INTO oral_history_track (
#                             track_number ,
#                             file_name ,
#                             file_format ,
#                             track_duration ,
#                             date_of_recording ,
#                             track_transcription_complete ,
#                             track_editing_remarks ,
#                             track_comments ,
#                             access_condition ,
#                             catalogued_by ,
#                             catalogued_date ,
#                             upload_date ,
#                             uploaded_by_user_of_id
#                     ) VALUES (
#                             :track_number ,
#                             :file_name ,
#                             :file_format ,
#                             :track_duration ,
#                             :recording_date ,
#                             :transcription_status,
#                             :track_editing_remarks ,
#                             :comments ,
#                             :access_condition ,
#                             :catalogued_by ,
#                             :catalogued_date ,
#                             :upload_date ,
#                             :uploaded_by_user_of_id
#                     ) """
#                 ),
#                 df_params.to_dicts(),
#             )

#             connection.execute(
#                 text(
#                     """
#                 INSERT INTO oral_history
#                 (
#                     interview_name ,
#                     recording_date ,
#                     total_tracks ,
#                     total_run_time ,
#                     access_condition ,
#                     access_remarks ,
#                     primary_language,
#                     interview_location_id ,
#                     interviewer_ids ,
#                     interviewee_ids ,
#                     comments ,
#                     uploaded_by_user_of_id,
#                     upload_date
#                 ) VALUES(
#                     :file_name ,
#                     :recording_date ,
#                     :total_tracks ,
#                     :track_duration ,
#                     :access_condition ,
#                     :access_remarks ,
#                     :primary_language ,
#                     :interview_location_id ,
#                     :interviewer_ids ,
#                     :interviewee_ids ,
#                     :comments ,
#                     :uploaded_by_user_of_id,
#                     :upload_date
#                 )
#                                             """
#                 ),
#                 df_grouped.to_dicts(),
#             )
#     except IntegrityError as e:
#         pass


@router.get("/DownloadTemplatesForTheCatalogs")
def download_templates_for_the_catalogs(token: str = Depends(route_auth_by_token)):
    file_path = "./templates for the catalogs.zip"
    return FileResponse(file_path, media_type="application/zip")
