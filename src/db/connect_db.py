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
