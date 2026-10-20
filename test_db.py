from sqlalchemy import create_engine, text
from src.config import DB_URL

engine = create_engine(DB_URL)
with engine.connect() as conn:
    print(conn.execute(text("SELECT version();")).scalar())
    print(conn.execute(text("SELECT current_database();")).scalar())