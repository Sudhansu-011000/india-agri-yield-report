CREATE SCHEMA IF NOT EXISTS core;

DROP TABLE IF EXISTS core.crop_production;

CREATE TABLE core.crop_production (
    source_id             INTEGER PRIMARY KEY,
    year_start            SMALLINT NOT NULL,
    fiscal_year           TEXT     NOT NULL,
    state_code            INTEGER,
    state_name            TEXT     NOT NULL,
    district_code         INTEGER,
    district_name         TEXT     NOT NULL,
    crop_id               INTEGER  NOT NULL,
    crop_code_raw         INTEGER,
    crop_name_raw         TEXT     NOT NULL,
    crop_name_clean       TEXT     NOT NULL,
    product_stage         TEXT,
    crop_type             TEXT,
    unit_basis            TEXT     NOT NULL,
    in_scope              BOOLEAN  NOT NULL,
    season                TEXT     NOT NULL,
    area                  NUMERIC,
    production            NUMERIC,
    yield_reported        NUMERIC,
    yield_calc            NUMERIC,
    is_production_missing BOOLEAN  NOT NULL DEFAULT FALSE,
    is_zero_production    BOOLEAN  NOT NULL DEFAULT FALSE,
    is_yield_mismatch     BOOLEAN  NOT NULL DEFAULT FALSE,
    is_outlier            BOOLEAN  NOT NULL DEFAULT FALSE,
    is_season_total       BOOLEAN  NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_core_crop_year ON core.crop_production (crop_id, year_start);
CREATE INDEX IF NOT EXISTS idx_core_state     ON core.crop_production (state_name);