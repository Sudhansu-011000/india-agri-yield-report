"""Builds mappings/crop_name_map.csv from the distinct crop names in staging.

Run once, then review and edit the CSV by hand. The pipeline reads the CSV,
so every cleaning decision about crop names lives in one visible file.
"""
import pandas as pd
from pathlib import Path

OUT = Path("mappings/crop_name_map.csv")

# raw name -> clean name (only real typos / spelling variants)
NAME_FIXES = {
    "Arcanut (Processed)": "Arecanut",
    "Atcanut (Raw)": "Arecanut",
    "Cashewnut Raw": "Cashewnut",
    "Cashewnut Processed": "Cashewnut",
    "Redish": "Radish",
    "Colocosia": "Colocasia",
    "Pome Granet": "Pomegranate",
    "Ribed Guard": "Ridged Gourd",
    "Snak Guard": "Snake Gourd",
    "Sannhamp": "Sunn Hemp",
    "Rapeseed &Mustard": "Rapeseed & Mustard",
}

# raw name -> product stage (kept as a column, rows are NOT merged)
STAGE = {
    "Arcanut (Processed)": "processed",
    "Atcanut (Raw)": "raw",
    "Cashewnut Raw": "raw",
    "Cashewnut Processed": "processed",
}

# Crops whose 'Tonnes' / 'Tonnes per Hectare' values are not plausible tonnes.
# Based on median yields (see reports/crop_coverage.csv), NOT on source metadata.
UNIT_BASIS = {
    "Coconut": "nuts",
    "Cotton(Lint)": "bales",
    "Jute": "bales",
    "Mesta": "bales",
    "Jute & Mesta": "bales",
}

IN_SCOPE = [
    "Rice", "Wheat", "Maize", "Jowar", "Bajra",
    "Gram", "Arhar/Tur", "Moong(Green Gram)", "Urad",
    "Groundnut", "Rapeseed & Mustard", "Soyabean",
    "Sugarcane", "Potato", "Onion",
]


def build(raw_names):
    df = pd.DataFrame({"crop_name_raw": sorted(set(raw_names))})
    df["crop_name_clean"] = df["crop_name_raw"].map(NAME_FIXES).fillna(df["crop_name_raw"])
    df["product_stage"] = df["crop_name_raw"].map(STAGE)
    df["unit_basis"] = df["crop_name_raw"].map(UNIT_BASIS).fillna("tonnes")
    df["in_scope"] = df["crop_name_clean"].isin(IN_SCOPE)
    clean_sorted = sorted(df["crop_name_clean"].unique())
    ids = {name: i + 1 for i, name in enumerate(clean_sorted)}
    df["crop_id"] = df["crop_name_clean"].map(ids)
    return df[["crop_id", "crop_name_raw", "crop_name_clean", "product_stage", "unit_basis", "in_scope"]]


def main():
    from sqlalchemy import create_engine
    from src.config import DB_URL
    names = pd.read_sql("SELECT DISTINCT crop_name FROM staging.crop_raw", create_engine(DB_URL))["crop_name"]
    OUT.parent.mkdir(exist_ok=True)
    build(names).to_csv(OUT, index=False)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()