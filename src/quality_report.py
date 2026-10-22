"""Phase 5: before/after data quality report.

'Before' is measured on the raw CSV, 'after' on core.crop_production and
core.crop_annual, using the same definitions. Each check counts rows where an
issue is still present AND unhandled (not fixed and not flagged).
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.clean.build_crop_map import NAME_FIXES, UNIT_BASIS

RAW = Path("data/raw/crop-wise-area-production-yield.csv")
REPORTS = Path("reports")

RAW_KEYS = ["year", "state_name", "district_name", "crop_name", "season"]
ANNUAL_KEY = ["year_start", "state_code", "district_code", "crop_name_raw"]
CORE_KEY = ANNUAL_KEY + ["season"]
CORE_REQUIRED = ["fiscal_year", "state_name", "district_name", "crop_name_raw", "season"]

VARIANT_NAMES = list(NAME_FIXES)
NON_TONNAGE = list(UNIT_BASIS)


def _fence(yield_s, crop_key, eligible):
    """Rows above Q3 + 3*IQR of yield within each crop (eligible, positive yields only)."""
    base = yield_s.where(eligible & (yield_s > 0))
    grp = base.groupby(crop_key)
    q1 = grp.transform(lambda s: s.quantile(0.25))
    q3 = grp.transform(lambda s: s.quantile(0.75))
    return (base > q3 + 3 * (q3 - q1)).fillna(False)


def before_flags(raw):
    """Row-level issue flags on the raw file."""
    clean = raw["crop_name"].map(NAME_FIXES).fillna(raw["crop_name"])
    non_t = raw["crop_name"].isin(NON_TONNAGE)
    ok = (raw["area"] > 0) & raw["production"].notna()
    ycalc = (raw["production"] / raw["area"]).where(ok)
    return pd.DataFrame({
        "placeholder_yield": raw["production"].isna() & raw["yield"].notna(),
        "missing_crop_code": raw["crop_code"].isna(),
        "crop_name_variant": raw["crop_name"].isin(VARIANT_NAMES),
        "shared_crop_code": raw.groupby("crop_code")["crop_name"].transform("nunique").gt(1),
        "unlabelled_non_tonnage": non_t,
        "unflagged_outlier": _fence(ycalc, clean, ~non_t),
        "total_overlap": raw["season"].eq("Total"),
    })


def after_flags(core, annual):
    """Row-level 'still present and unhandled' flags on the cleaned core table."""
    flags = pd.DataFrame({
        "placeholder_yield": core["production"].isna() & core["yield_reported"].notna(),
        "missing_crop_code": core["crop_id"].isna(),
        "crop_name_variant": core["crop_name_clean"].isin(VARIANT_NAMES),
        "shared_crop_code": core.groupby("crop_id")["crop_name_clean"].transform("nunique").gt(1),
        "unlabelled_non_tonnage": core["crop_name_raw"].isin(NON_TONNAGE) & (core["unit_basis"] == "tonnes"),
        "unflagged_outlier": _fence(core["yield_calc"], core["crop_id"], core["unit_basis"] == "tonnes")
                             & ~core["is_outlier"],
    })
    # Total rows that are not used as the annual figure (cannot be tied to one row)
    total_rows = int(core["is_season_total"].sum())
    used = int((annual["annual_source"] == "total").sum())
    return flags, max(total_rows - used, 0)


def _yield_mismatch_raw(raw):
    ok = (raw["area"] > 0) & raw["production"].notna() & raw["yield"].notna()
    calc = raw["production"] / raw["area"]
    tol = np.maximum(0.05 * raw["yield"].fillna(0), 0.001)
    return int((ok & ((calc - raw["yield"]).abs() > tol)).sum())


def build_report(raw, core, annual):
    bf = before_flags(raw)
    af, total_unresolved = after_flags(core, annual)

    handled = {
        "placeholder_yield": int(core["is_production_missing"].sum()),
        "missing_crop_code": int(core["crop_code_raw"].isna().sum()),
        "crop_name_variant": int((core["crop_name_raw"] != core["crop_name_clean"]).sum()),
        "shared_crop_code": int(core.groupby("crop_code_raw")["crop_name_raw"].transform("nunique").gt(1).sum()),
        "unlabelled_non_tonnage": int((core["unit_basis"] != "tonnes").sum()),
        "unflagged_outlier": int(core["is_outlier"].sum()),
        "total_overlap": int(core["is_season_total"].sum()),
    }
    labels = {
        "placeholder_yield": ("Completeness", "Fake yield of 0 stored where production is blank"),
        "missing_crop_code": ("Completeness", "Crop identifier missing"),
        "crop_name_variant": ("Validity", "Crop name is a known variant or typo"),
        "unlabelled_non_tonnage": ("Validity", "Non-tonnage crop (nuts/bales) not labelled"),
        "unflagged_outlier": ("Validity", "Extreme yield outlier not flagged"),
        "shared_crop_code": ("Consistency", "Crop code shared by different crops"),
        "total_overlap": ("Consistency", "Total row overlaps its own seasons (double-count risk)"),
    }
    rows = []
    for k, (dim, text) in labels.items():
        before = int(bf[k].sum())
        after = total_unresolved if k == "total_overlap" else int(af[k].sum())
        rows.append((dim, text, before, after, handled[k]))

    # Checks that pass both before and after (reported for completeness)
    rows.append(("Consistency", "Reported yield differs from production / area (rounding-aware)",
                 _yield_mismatch_raw(raw), int(core["is_yield_mismatch"].sum()), 0))
    rows.append(("Completeness", "Required fields blank (year, state, district, crop, season)",
                 int(raw[RAW_KEYS].isna().sum().sum()), int(core[CORE_REQUIRED].isna().sum().sum()), 0))
    rows.append(("Consistency", "Duplicate keys",
                 int(raw.duplicated(RAW_KEYS).sum()),
                 int(annual.duplicated(ANNUAL_KEY).sum() + core.duplicated(CORE_KEY).sum()), 0))

    table = pd.DataFrame(rows, columns=["dimension", "check", "rows_before",
                                        "rows_unresolved_after", "rows_handled_after"])

    # Summary
    n_before, n_after = len(raw), len(core)
    hidden_before = int(bf.any(axis=1).sum())
    hidden_after = int(af.any(axis=1).sum())
    visible = (core["is_production_missing"] | core["is_zero_production"] | core["is_outlier"]
               | core["is_season_total"] | (core["unit_basis"] != "tonnes") | core["is_yield_mismatch"])
    s_core, s_ann = core[core["in_scope"]], annual[annual["in_scope"]]
    over_area = (s_core["area"].sum() / s_ann["area_annual"].sum() - 1) * 100
    over_prod = (s_core["production"].sum() / s_ann["production_annual"].sum() - 1) * 100

    summary = pd.DataFrame([
        ("Checks with zero unresolved rows (out of %d)" % len(table),
         int((table["rows_before"] == 0).sum()), int((table["rows_unresolved_after"] == 0).sum())),
        ("Rows with at least one hidden issue", hidden_before, hidden_after),
        ("Rows with at least one hidden issue (%)",
         round(hidden_before / n_before * 100, 2), round(hidden_after / n_after * 100, 2)),
        ("Rows carrying a visible flag (issue marked, not hidden)", 0, int(visible.sum())),
        ("In-scope area overstated if all rows are summed (%)", round(over_area, 1), 0.0),
        ("In-scope production overstated if all rows are summed (%)", round(over_prod, 1), 0.0),
        ("Distinct crop names / crops", int(raw["crop_name"].nunique()), int(core["crop_name_clean"].nunique())),
        ("Rows in analysis table", n_before, len(annual)),
    ], columns=["metric", "before", "after"], dtype=object)
    return table, summary


def main():
    from sqlalchemy import create_engine
    from src.config import DB_URL
    from src.clean.annual import ANNUAL_COLS
    from src.clean.pipeline import CORE_COLS

    raw = pd.read_csv(RAW)
    engine = create_engine(DB_URL)
    core = pd.read_sql(f"SELECT {', '.join(CORE_COLS)} FROM core.crop_production", engine, coerce_float=True)
    annual = pd.read_sql(f"SELECT {', '.join(ANNUAL_COLS)} FROM core.crop_annual", engine, coerce_float=True)

    table, summary = build_report(raw, core, annual)
    REPORTS.mkdir(exist_ok=True)
    table.to_csv(REPORTS / "data_quality_before_after.csv", index=False)
    summary.to_csv(REPORTS / "data_quality_summary.csv", index=False)
    pd.set_option("display.width", 220, "display.max_colwidth", 70)
    print(table.to_string(index=False))
    print()
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
