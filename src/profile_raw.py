import pandas as pd
import numpy as np
from pathlib import Path

RAW = Path("data/raw/crop-wise-area-production-yield.csv")
OUT = Path("reports")
OUT.mkdir(exist_ok=True)

df = pd.read_csv(RAW)
keys = ["year", "state_name", "district_name", "crop_name", "season"]
m = {}

# --- Size and completeness ---
m["rows"] = len(df)
m["columns"] = df.shape[1]
m["missing_production"] = int(df["production"].isna().sum())
m["missing_area"] = int(df["area"].isna().sum())
m["missing_crop_code"] = int(df["crop_code"].isna().sum())
m["zero_production"] = int((df["production"] == 0).sum())

# --- Duplicates ---
m["exact_duplicates_excl_id"] = int(df.drop(columns="id").duplicated().sum())
m["duplicate_keys"] = int(df.duplicated(keys).sum())

# --- Season overlap (double-counting risk) ---
g = df.groupby(["year", "state_name", "district_name", "crop_name"])["season"].agg(set)
m["groups_total_plus_other_seasons"] = int(g.apply(lambda s: "Total" in s and len(s) > 1).sum())
m["groups_wholeyear_plus_other_seasons"] = int(g.apply(lambda s: "Whole Year" in s and len(s) > 1).sum())

# --- Crop code collisions ---
cc = df.groupby("crop_code")["crop_name"].nunique()
m["crop_codes_shared_by_multiple_names"] = int((cc > 1).sum())

# --- Yield consistency ---
ok = df["area"] > 0
calc = df["production"] / df["area"]
rel = (calc - df["yield"]).abs() / df["yield"].replace(0, np.nan)
m["yield_mismatch_gt_5pct"] = int((ok & (rel > 0.05)).sum())

# --- Outliers (3 x IQR within each crop) ---
def upper_outliers(s):
    q1, q3 = s.quantile([0.25, 0.75])
    return (s > q3 + 3 * (q3 - q1)).sum()

m["yield_outliers_3iqr"] = int(df.groupby("crop_name")["yield"].apply(upper_outliers).sum())

pd.Series(m, name="value").to_csv(OUT / "baseline_quality.csv")

# --- Supporting tables ---
df.groupby("state_name").agg(
    rows=("id", "size"), districts=("district_code", "nunique"), years=("year", "nunique")
).sort_values("rows", ascending=False).to_csv(OUT / "state_coverage.csv")

df.groupby("crop_name").agg(
    rows=("id", "size"), years=("year", "nunique"), states=("state_name", "nunique"),
    pct_missing_production=("production", lambda s: round(s.isna().mean() * 100, 2)),
    median_yield=("yield", "median"),
).sort_values("rows", ascending=False).to_csv(OUT / "crop_coverage.csv")

df.groupby("year")["district_code"].nunique().to_csv(OUT / "districts_by_year.csv")

df.groupby(["crop_name", "season"]).size().unstack(fill_value=0).to_csv(OUT / "crop_season_counts.csv")

print(pd.Series(m))