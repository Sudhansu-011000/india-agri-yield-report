CREATE SCHEMA IF NOT EXISTS core;

DROP TABLE IF EXISTS core.crop_annual;

CREATE TABLE core.crop_annual (
    year_start            SMALLINT NOT NULL,
    fiscal_year           TEXT     NOT NULL,
    state_code            INTEGER  NOT NULL,
    state_name            TEXT     NOT NULL,
    district_code         INTEGER  NOT NULL,
    district_name         TEXT     NOT NULL,
    crop_id               INTEGER  NOT NULL,
    crop_name_raw         TEXT     NOT NULL,
    crop_name_clean       TEXT     NOT NULL,
    product_stage         TEXT,
    crop_type             TEXT,
    unit_basis            TEXT     NOT NULL,
    in_scope              BOOLEAN  NOT NULL,
    annual_source         TEXT     NOT NULL,      -- 'total' or 'sum_of_rows'
    n_source_rows         INTEGER  NOT NULL,
    has_whole_year        BOOLEAN  NOT NULL,
    area_annual           NUMERIC,
    production_annual     NUMERIC,
    yield_annual          NUMERIC,
    is_production_missing BOOLEAN  NOT NULL DEFAULT FALSE,
    is_zero_production    BOOLEAN  NOT NULL DEFAULT FALSE,
    is_total_mismatch     BOOLEAN  NOT NULL DEFAULT FALSE,
    is_outlier            BOOLEAN  NOT NULL DEFAULT FALSE,
    PRIMARY KEY (year_start, state_code, district_code, crop_name_raw)
);

CREATE INDEX IF NOT EXISTS idx_annual_crop_year  ON core.crop_annual (crop_id, year_start);
CREATE INDEX IF NOT EXISTS idx_annual_state_year ON core.crop_annual (state_code, year_start);

-- Season-detail level: individual seasons only, never mixed with Total
CREATE OR REPLACE VIEW core.v_season_detail AS
SELECT * FROM core.crop_production
WHERE NOT is_season_total;