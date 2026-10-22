"""Phase 3 cleaning pipeline: staging.crop_raw -> core.crop_production."""
import io
from pathlib import Path

import numpy as np
import pandas as pd

MAP_PATH = Path("mappings/crop_name_map.csv")
REPORTS = Path("reports")

CORE_COLS = [
    "source_id", "year_start", "fiscal_year",
    "state_code", "state_name", "district_code", "district_name",
    "crop_id", "crop_code_raw", "crop_name_raw", "crop_name_clean", "product_stage",
    "crop_type", "unit_basis", "in_scope", "season",
    "area", "production", "yield_reported", "yield_calc",
    "is_production_missing", "is_zero_production",
    "is_yield_mismatch", "is_outlier", "is_season_total",
]

STEPS = []  # (step, issue, rows_affected)


def note(step, issue, n):
    STEPS.append((step, issue, int(n)))
    print(f"[{step}] {issue}: {int(n):,}")


# ---------------------------------------------------------------- step 1
def fix_types(df):
    df = df.copy()
    df = df.replace(r"^\s*$", np.nan, regex=True)          # blank text -> NULL

    for col in ["area", "production", "yield"]:
        before = df[col].isna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        note("1-types", f"{col}: values lost during numeric conversion",
             df[col].isna().sum() - before)

    for col in ["id", "state_code", "district_code", "crop_code"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in ["state_name", "district_name", "crop_name", "season", "crop_type"]:
        df[col] = df[col].str.strip()

    df["year_start"] = df["year"].str[:4].astype(int)
    df["fiscal_year"] = df["year"].str[:4] + "-" + df["year"].str[7:]
    return df

# ---------------------------------------------------------------- step 1b
REQUIRED = ["year", "state_name", "district_name", "crop_name", "season"]


def recover_names_from_codes(df):
    """If a state/district name is blank but its code is known, copy the name
    from other rows with the same code. Anything still blank becomes 'Unknown'."""
    df = df.copy()
    rules = [("state_name", ["state_code"]),
             ("district_name", ["state_code", "district_code"])]
    for name_col, code_cols in rules:
        missing = df[name_col].isna()
        note("1b-names", f"{name_col} blank in staging", missing.sum())
        if not missing.any():
            continue
        known = df.loc[~missing & df[code_cols].notna().all(axis=1), code_cols + [name_col]]
        lookup = (known.groupby(code_cols)[name_col]
                  .agg(lambda s: s.mode().iat[0]).rename("_rec").reset_index())
        rec = df.loc[missing, code_cols].merge(lookup, on=code_cols, how="left")["_rec"].values
        df.loc[missing, name_col] = rec
        still = df[name_col].isna()
        note("1b-names", f"{name_col} recovered from code", missing.sum() - still.sum())
        if still.any():
            df.loc[still, name_col] = "Unknown"
            note("1b-names", f"{name_col} set to 'Unknown' (no code match)", still.sum())
    return df


def check_required(df):
    """Fail with a readable message instead of a database error."""
    bad = {c: int(df[c].isna().sum()) for c in REQUIRED if df[c].isna().any()}
    if bad:
        raise ValueError(f"Required columns still have blanks: {bad}. "
                         "Inspect these rows in staging.crop_raw before continuing.")

# ---------------------------------------------------------------- step 2
def flag_missing_vs_zero(df):
    df = df.copy()
    df["is_production_missing"] = df["production"].isna()
    df["is_zero_production"] = (df["production"] == 0) & (df["area"] > 0)
    df["yield_reported"] = df["yield"]

    # The source wrote yield = 0 where production was blank. That is a placeholder.
    placeholder = df["is_production_missing"] & df["yield_reported"].notna()
    df.loc[df["is_production_missing"], "yield_reported"] = np.nan
    note("2-missing", "production blank (kept as NULL, flagged)", df["is_production_missing"].sum())
    note("2-missing", "placeholder yield reset to NULL", placeholder.sum())
    note("2-missing", "production = 0 with area > 0 (kept, flagged)", df["is_zero_production"].sum())
    return df


# ---------------------------------------------------------------- step 3
def map_crops(df, crop_map):
    df = df.merge(crop_map, left_on="crop_name", right_on="crop_name_raw", how="left")
    unmapped = df["crop_id"].isna().sum()
    if unmapped:
        raise ValueError(f"{unmapped} rows have a crop name missing from crop_name_map.csv: "
                         f"{df.loc[df['crop_id'].isna(), 'crop_name'].unique()[:10]}")
    df = df.rename(columns={"crop_code": "crop_code_raw"})
    note("3-crops", "rows whose crop name was changed",
         (df["crop_name_raw"] != df["crop_name_clean"]).sum())
    note("3-crops", "rows with non-tonnage unit basis (nuts / bales)",
         (df["unit_basis"] != "tonnes").sum())
    return df


# ---------------------------------------------------------------- step 4
def reconcile_yield(df):
    df = df.copy()
    ok = (df["area"] > 0) & df["production"].notna()
    df["yield_calc"] = np.where(ok, df["production"] / df["area"], np.nan)

    rep = df["yield_reported"]
    diff = (df["yield_calc"] - rep).abs()
    tol = np.maximum(0.05 * rep.fillna(0), 0.001)         # 5% or rounding (3 decimals)
    df["is_yield_mismatch"] = ok & rep.notna() & (diff > tol)
    note("4-yield", "reported yield differs from production / area", df["is_yield_mismatch"].sum())
    return df


# ---------------------------------------------------------------- step 5
def flag_outliers(df):
    df = df.copy()
    base = df["yield_calc"].where((df["unit_basis"] == "tonnes") & (df["yield_calc"] > 0))
    grp = base.groupby(df["crop_id"])
    q1, q3 = grp.transform(lambda s: s.quantile(0.25)), grp.transform(lambda s: s.quantile(0.75))
    df["is_outlier"] = (base > q3 + 3 * (q3 - q1)).fillna(False)
    note("5-outliers", "yield above Q3 + 3*IQR within crop (flag only)", df["is_outlier"].sum())
    return df


# ---------------------------------------------------------------- step 6
def flag_seasons(df):
    df = df.copy()
    df["is_season_total"] = df["season"] == "Total"
    note("6-season", "rows with season = Total (kept, flagged)", df["is_season_total"].sum())
    return df


# ---------------------------------------------------------------- run
def transform(raw, crop_map):
    STEPS.clear()
    df = fix_types(raw)
    df = recover_names_from_codes(df)
    check_required(df)
    df = flag_missing_vs_zero(df)
    df = map_crops(df, crop_map)
    df = reconcile_yield(df)
    df = flag_outliers(df)
    df = flag_seasons(df)
    df = df.rename(columns={"id": "source_id"})
    return df[CORE_COLS]


def load_core(df, engine):
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False)
    buf.seek(0)
    cols = ", ".join(CORE_COLS)
    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        cur.execute("TRUNCATE core.crop_production")
        cur.copy_expert(f"COPY core.crop_production ({cols}) FROM STDIN WITH (FORMAT csv)", buf)
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def main():
    from sqlalchemy import create_engine
    from src.config import DB_URL

    engine = create_engine(DB_URL)
    raw = pd.read_sql("SELECT * FROM staging.crop_raw", engine)
    crop_map = pd.read_csv(MAP_PATH)
    print(f"Read {len(raw):,} rows from staging")

    clean = transform(raw, crop_map)
    load_core(clean, engine)

    REPORTS.mkdir(exist_ok=True)
    pd.DataFrame(STEPS, columns=["step", "issue", "rows_affected"]).to_csv(
        REPORTS / "cleaning_step_counts.csv", index=False)
    print(f"Loaded {len(clean):,} rows into core.crop_production")


if __name__ == "__main__":
    main()