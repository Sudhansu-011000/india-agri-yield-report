import sys
from sqlalchemy import create_engine
from src.config import DB_URL

path = sys.argv[1]
sql = open(path, encoding="utf-8").read()

raw = create_engine(DB_URL).raw_connection()
try:
    cur = raw.cursor()
    cur.execute(sql)
    raw.commit()
    print(f"Ran {path}")
finally:
    raw.close()