"""Phase 4: build one annual row per year, district and crop (no double-counting).

Rule (per year + state + district + crop):
  1. If a 'Total' row exists, use it.
  2. Otherwise add up every row in the group (individual seasons AND 'Whole Year').
Evidence: 'Whole Year' behaves as one more season that is added into Total.
"""
import io
from pathlib import Path

import numpy as np
import pandas as pd

REPORTS = Path("reports")
KEY = ["year_start", "state_code", "district_code", "crop_name_raw"]
ATTR = ["fiscal_year", "state_name", "district_name", "crop_id", "crop_name_clean",
        "product_stage", "crop_type", "unit_basis", "in_scope"]

ANNUAL_COLS = [
    "year_start", "fiscal_year", "state_code", "state_name", "district_code", "district_name",
    "crop_id", "crop_name_raw", "crop_name_clean", "product_stage", "crop_type",
    "unit_basis", "in_scope", "annual_source", "n_source_rows", "has_whole_year",
    "area_annual", "production_annual", "yield_annual",
    "is_production_missing", "is_zero_production", "is_total_mismatch", "is_outlier",
]

STEPS = []


def note(step, issue, n):
    STEPS.append((step, issue, int(n)))
    print(f"[{step}] {issue}: {int(n):,}")


def _differs(a, b, rel=0.001, floor=0.01):
    """True where a and b differ by more than rel (relative) and the floor."""
    return (a - b).abs() > np.maximum(rel * a.abs(), floor)


def build_annual(df):
    STEPS.clear()
    d = df.copy()
    d["_prod_null"] = d["production"].isna()
    d["_is_wy"] = d["season"] == "Whole Year"

    base = d.groupby(KEY)[ATTR].first()

    totals = (d[d["is_season_total"]]
              .groupby(KEY)[["area", "production"]].first()
              .rename(columns={"area": "total_area", "production": "total_production"}))

    others = (d[~d["is_season_total"]]
              .groupby(KEY)
              .agg(sum_area=("area", "sum"),
                   sum_production=("production", "sum"),
                   any_null_prod=("_prod_null", "max"),
                   n_rows=("season", "size"),
                   has_wy=("_is_wy", "max")))

    a = base.join(totals, how="left").join(others, how="left")
    has_total = a["total_area"].notna()

    a["annual_source"] = np.where(has_total, "total", "sum_of_rows")
    a["n_source_rows"] = a["n_rows"].fillna(0).astype(int) + has_total.astype(int)
    a["has_whole_year"] = a["has_wy"].fillna(False).astype(bool)

    a["area_annual"] = np.where(has_total, a["total_area"], a["sum_area"])
    sum_prod = a["sum_production"].where(~a["any_null_prod"].fillna(False).astype(bool))
    a["production_annual"] = np.where(has_total, a["total_production"], sum_prod)

    ok = (a["area_annual"] > 0) & a["production_annual"].notna()
    a["yield_annual"] = np.where(ok, a["production_annual"] / a["area_annual"], np.nan)

    a["is_production_missing"] = a["production_annual"].isna()
    a["is_zero_production"] = (a["production_annual"] == 0) & (a["area_annual"] > 0)

    # Does the source's Total agree with the sum of its own rows?
    area_bad = has_total & _differs(a["total_area"], a["sum_area"])
    comparable = (has_total & a["total_production"].notna()
                  & ~a["any_null_prod"].fillna(False).astype(bool))
    prod_bad = comparable & _differs(a["total_production"], a["sum_production"])
    a["is_total_mismatch"] = area_bad | prod_bad

    # Outliers on the annual yield, within crop, tonnage crops only
    basey = a["yield_annual"].where((a["unit_basis"] == "tonnes") & (a["yield_annual"] > 0))
    grp = basey.groupby(a["crop_id"])
    q1 = grp.transform(lambda s: s.quantile(0.25))
    q3 = grp.transform(lambda s: s.quantile(0.75))
    a["is_outlier"] = (basey > q3 + 3 * (q3 - q1)).fillna(False)

    a = a.reset_index()

    note("A-rows", "source rows in", len(df))
    note("A-rows", "annual rows out (one per year, district, crop)", len(a))
    note("A-source", "annual figure taken from Total", (a["annual_source"] == "total").sum())
    note("A-source", "annual figure summed from rows", (a["annual_source"] == "sum_of_rows").sum())
    note("A-source", "groups with a Whole Year row alongside other rows",
         (a["has_whole_year"] & (a["n_source_rows"] > 1)).sum())
    note("A-quality", "Total disagrees with sum of its rows", a["is_total_mismatch"].sum())
    note("A-quality", "annual production missing", a["is_production_missing"].sum())
    note("A-quality", "annual production zero", a["is_zero_production"].sum())
    note("A-quality", "annual yield outliers (flag only)", a["is_outlier"].sum())
    return a[ANNUAL_COLS]


def load_annual(a, engine):
    buf = io.StringIO()
    a.to_csv(buf, index=False, header=False)
    buf.seek(0)
    cols = ", ".join(ANNUAL_COLS)
    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        cur.execute("TRUNCATE core.crop_annual")
        cur.copy_expert(f"COPY core.crop_annual ({cols}) FROM STDIN WITH (FORMAT csv)", buf)
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def main():
    from sqlalchemy import create_engine
    from src.config import DB_URL
    from src.clean.pipeline import CORE_COLS

    engine = create_engine(DB_URL)
    df = pd.read_sql(f"SELECT {', '.join(CORE_COLS)} FROM core.crop_production",
                     engine, coerce_float=True)
    print(f"Read {len(df):,} rows from core.crop_production")

    annual = build_annual(df)
    load_annual(annual, engine)

    REPORTS.mkdir(exist_ok=True)
    pd.DataFrame(STEPS, columns=["step", "issue", "rows_affected"]).to_csv(
        REPORTS / "annual_step_counts.csv", index=False)
    print(f"Loaded {len(annual):,} rows into core.crop_annual")


if __name__ == "__main__":
    main()