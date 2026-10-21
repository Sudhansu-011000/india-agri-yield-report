import csv
from pathlib import Path
from sqlalchemy import create_engine, text
from src.config import DB_URL

RAW = Path("data/raw/crop-wise-area-production-yield.csv")
TABLE = "staging.crop_raw"


def read_header():
    with open(RAW, encoding="utf-8-sig", newline="") as f:
        return [h.strip() for h in next(csv.reader(f))]


def count_csv_rows():
    with open(RAW, encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1  # minus header


def main():
    header = read_header()
    cols = ", ".join(f'"{h}"' for h in header)
    engine = create_engine(DB_URL)

    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        cur.execute(f"TRUNCATE {TABLE}")          # makes the script safe to re-run
        with open(RAW, encoding="utf-8-sig", newline="") as f:
            cur.copy_expert(
                f"COPY {TABLE} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true)", f
            )
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()

    with engine.connect() as conn:
        loaded = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar()

    expected = count_csv_rows()
    print(f"CSV rows: {expected:,} | Table rows: {loaded:,}")
    print("MATCH" if loaded == expected else "MISMATCH - investigate")


if __name__ == "__main__":
    main()