import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import polars as pl

load_dotenv()

engine = None
try:
    engine = create_engine(
        f"postgresql+psycopg2://{os.environ.get('user')}:{os.environ.get('password')}@{os.environ.get('host')}:{os.environ.get('port')}/{os.environ.get('database')}"
    )

    print(
        f"Connection to the {os.environ.get('host')} for user {os.environ.get('user')} created successfully."
    )

    with engine.begin() as connection:
        connection.execute(text("SET search_path TO public"))

        results = connection.execute(text("SELECT current_database();")).one()
        print("database name:", results)
        results = connection.execute(text("SELECT current_user;")).one()
        print("current database user:", results)
        print("connection", connection)

except Exception as ex:  # noqa: BLE001
    print("Connection could not be made due to the following error:\n", ex["details"])


def insert_into_person_if_not_exist_in_name_held(names, user_id, connection):
    if type(names) == str:
        names = [names]
    for name in names:
        result = connection.execute(
            text("SELECT 1 FROM person WHERE :name=ANY(name_held) LIMIT 1;"),
            [{"name": name}],
        ).first()
        if result is None:
            connection.execute(
                text(
                    """
            INSERT INTO person (name_held,uploaded_by_user_of_id,upload_date)
            VALUES (ARRAY [:name_held],:uploaded_by_user_of_id,:upload_date)
                """
                ),
                [
                    {
                        "name_held": name,
                        "uploaded_by_user_of_id": user_id,
                        "upload_date": "NOW()",
                    }
                ],
            )


def insert_into_locality(params, connection):
    connection.execute(
        text(
            """
                INSERT INTO locality 
                (locality_name,locality_rank,parent_locality,uploaded_by_user_of_id,upload_date)
                VALUES 
                (:locality_name,:locality_rank,:parent_locality,:uploaded_by_user_of_id,:upload_date)
            """
        ),
        [params],
    )


def get_all_people_from_person_table(connection):
    return pl.DataFrame(
        list(connection.execute(text("SELECT person_id, name_held FROM person")).all())
    ).explode("name_held")


def get_unique_localities(where=None, connection=None):
    sql = "SELECT DISTINCT locality_id,locality_name FROM locality "
    return connection.execute(text(sql if where is None else sql + where)).all()


def df_params_sorting_of_names_and_ids(
    df_params: pl.DataFrame,
    df2: pl.DataFrame,
    prefix=str,
    join_on_column=str,
    prefix2_for_join=str,
):
    df_params = (
        df_params.rename({prefix + "_name": join_on_column})
        .join(df2, join_on_column, how="left")
        .rename({prefix2_for_join + "_id": prefix + "_id"})
        .drop(join_on_column)
    )
    return df_params


def localities_params_dict_sorting_of_names_and_ids(
    df_params: pl.DataFrame, unique_localities, column_name_for_locality
):
    df_params = (
        df_params.rename({column_name_for_locality: "locality_name"})
        .join(unique_localities, "locality_name", how="left")
        .drop("locality_name")
        .rename({"locality_id": column_name_for_locality})
    )
    return df_params


def df_params_sorting_of_names_and_id_in_list_fields(
    df_params: pl.DataFrame,
    people,
    person_type,
    column_to_be_filtered: str,  # name_held
    column_to_be_extracted: str,  # person_id
):

    def fun_(x):
        arr = []
        for x1 in x:
            t = people.filter(pl.col(column_to_be_filtered) == x1)[
                column_to_be_extracted
            ].to_list()
            if len(t) != 0:
                arr.extend([int(t1) for t1 in t])
        return arr

    return df_params.with_columns(
        pl.col(person_type + "_names")
        .map_elements(fun_, pl.List(pl.Int16))
        .alias(person_type + "_ids")
    )


def find_if_locality_name_exists_in_db(locality, connection):
    sql = (
        """
                                SELECT 1
                                FROM locality
                                WHERE locality_name = :locality_name
                                LIMIT 1;
                                """
        if not isinstance(locality, tuple)
        else """
                                SELECT 1
                                FROM locality
                                WHERE locality_name IN :locality_name
                                LIMIT 1;
                                """
    )

    return connection.execute(
        text(sql),
        [{"locality_name": locality}],
    ).first()
