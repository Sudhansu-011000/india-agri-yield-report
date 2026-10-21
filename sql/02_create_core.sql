CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.crop_production (
    source_id             INTEGER PRIMARY KEY,
    year_start            SMALLINT NOT NULL,
    fiscal_year           TEXT     NOT NULL,
    state_code            INTEGER,
    state_name            TEXT     NOT NULL,
    district_code         INTEGER,
    district_name         TEXT     NOT NULL,
    crop_code             INTEGER,
    crop_name_raw         TEXT     NOT NULL,
    crop_name_clean       TEXT,
    season                TEXT     NOT NULL,
    crop_type             TEXT,
    area                  NUMERIC,
    production            NUMERIC,
    yield_reported        NUMERIC,
    yield_calc            NUMERIC,
    is_production_missing BOOLEAN DEFAULT FALSE,
    is_zero_production    BOOLEAN DEFAULT FALSE,
    is_yield_mismatch     BOOLEAN DEFAULT FALSE,
    is_outlier            BOOLEAN DEFAULT FALSE,
    is_season_total       BOOLEAN DEFAULT FALSE
);