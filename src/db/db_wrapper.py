import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

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
                                    INSERT INTO locality (locality_name,locality_rank,parent_locality,uploaded_by_user_of_id,upload_date)
                                    VALUES (:locality_name,:locality_rank,:parent_locality,:uploaded_by_user_of_id,:upload_date)
                                    """
        ),
        [params],
    )


def get_all_people_from_person_table(connection):
    return list(
        connection.execute(text("SELECT person_id, name_held FROM person")).all()
    )


def get_unique_localities(where=None, connection=None):
    sql = "SELECT DISTINCT locality_id,locality_name FROM locality "
    return connection.execute(text(sql if where is None else sql + where)).all()


# only used once in files.py
def param_dict_sorting_of_names_and_ids(
    params_dict: dict,
    people: list,
    column_name_for_person_name: str,
    column_name_for_person_id: str,
    connection,
):
    # print("params dict ", params_dict)
    for x in params_dict:
        hasChanged = False
        for person in people:
            # print(x[column_name_for_person_name], person[1])
            if (
                x[column_name_for_person_name] in person[1]
                # 1 index points to name_held in person
            ):  # name_held in people
                # print("person 0", person[0])
                x[column_name_for_person_id] = person[0]  # persion_id in people
                hasChanged = True

        if not hasChanged:
            x[column_name_for_person_id] = None
        del x[column_name_for_person_name]


def localities_params_dict_sorting_of_names_and_ids(
    params_dict, people, unique_localities, column_name_for_locality, connection
):
    for x in params_dict:
        hasChanged = False
        for l in unique_localities.iter_rows():
            if x[column_name_for_locality] == l[1]:  # locality (name)
                x[column_name_for_locality] = l[0]  # locality_id
                hasChanged = True
                # break

        if not hasChanged:
            x[column_name_for_locality] = None


def param_dict_sorting_of_names_and_id_for_interview_participants(
    params_dict,
    people,
    column_name_for_interview_participant_name,
    column_name_for_interview_participant_id,
    connection,
):
    for x in params_dict:
        hasChanged = False
        new_interview_participant_ids = []
        if x[column_name_for_interview_participant_name] == None:
            x[column_name_for_interview_participant_id] = None
            continue
        for person in people:
            for ip in x[column_name_for_interview_participant_name]:
                if (
                    ip in person[1]
                    # 1 index points to name_held in person
                ):
                    # print("person 0", person[0])
                    new_interview_participant_ids.append(
                        person[0]
                    )  # persion_id in people
                    hasChanged = True

        x[column_name_for_interview_participant_id] = (
            new_interview_participant_ids if hasChanged else None
        )
        del x[column_name_for_interview_participant_name]


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
