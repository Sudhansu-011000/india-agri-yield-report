CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.crop_raw (
    id              TEXT,
    year            TEXT,
    state_code      TEXT,
    state_name      TEXT,
    district_code   TEXT,
    district_name   TEXT,
    crop_code       TEXT,
    crop_name       TEXT,
    season          TEXT,
    crop_type       TEXT,
    area            TEXT,
    area_unit       TEXT,
    production      TEXT,
    production_unit TEXT,
    "yield"         TEXT,
    yield_unit      TEXT,
    _loaded_at      TIMESTAMPTZ DEFAULT now(),
    _source_file    TEXT DEFAULT 'crop-wise-area-production-yield.csv'
);