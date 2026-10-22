"""Small helpers that build tiny staging-shaped data for unit tests."""
import pandas as pd

RAW_COLS = ["id", "year", "state_name", "state_code", "district_name", "district_code",
            "crop_name", "crop_code", "crop_type", "season", "area", "area_unit",
            "production", "production_unit", "yield", "yield_unit"]

CROP_MAP = pd.DataFrame({
    "crop_id": [1, 2],
    "crop_name_raw": ["Rice", "Coconut"],
    "crop_name_clean": ["Rice", "Coconut"],
    "product_stage": [None, None],
    "unit_basis": ["tonnes", "nuts"],
    "in_scope": [True, False],
})


def row(id, season="Kharif", area="100", production="200", yld="2.0", crop="Rice",
        district="Alpha", dcode="1", state="Odisha", scode="21", year="2010-2011", ccode="101"):
    return [str(id), year, state, scode, district, dcode, crop, ccode, "Cereals", season,
            area, "Hectare", production, "Tonnes", yld, "Tonnes/Hectare"]


def make_raw(*rows):
    """Text columns with None for blanks, like a read from staging.crop_raw."""
    df = pd.DataFrame(list(rows), columns=RAW_COLS).astype(object)
    return df.where(df.notna(), None)
