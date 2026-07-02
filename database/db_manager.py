import sqlite3
import logging
from pathlib import Path

from platformdirs import user_data_dir


logger = logging.getLogger(__name__)
DB_PATH = Path(user_data_dir(appname="Atomic", appauthor="Maxwell"))

def initialize():
    DB_PATH.mkdir(parents=True, exist_ok=True)
    logger.info(f"DB path: {DB_PATH}")
    db_file = DB_PATH / "atomic.db"
    with sqlite3.connect(db_file) as db:
        cursor = db.cursor()
        with open('database/schema.sql') as schema_file:
            schema = schema_file.read()
            cursor.executescript(schema)
        db.commit()
        cursor.close()






