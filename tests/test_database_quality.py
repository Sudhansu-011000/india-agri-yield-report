"""Integration tests on the real PostgreSQL tables. Skipped if the database is unreachable."""
import pytest
from sqlalchemy import create_engine, text

from src.config import DB_URL


@pytest.fixture(scope="module")
def conn():
    try:
        c = create_engine(DB_URL).connect()
    except Exception as exc:
        pytest.skip(f"database not reachable: {exc}")
    yield c
    c.close()


def scalar(conn, sql):
    return conn.execute(text(sql)).scalar()


# ---- nothing lost, nothing invalid -------------------------------------------------
def test_no_rows_lost_between_staging_and_core(conn):
    assert scalar(conn, "SELECT COUNT(*) FROM staging.crop_raw") == \
           scalar(conn, "SELECT COUNT(*) FROM core.crop_production")


def test_no_negative_area_or_production(conn):
    sql = ("SELECT COUNT(*) FROM core.crop_production "
           "WHERE area < 0 OR production < 0")
    assert scalar(conn, sql) == 0


def test_no_blank_required_fields(conn):
    sql = ("SELECT COUNT(*) FROM core.crop_production WHERE state_name IS NULL "
           "OR district_name IS NULL OR crop_name_raw IS NULL OR season IS NULL")
    assert scalar(conn, sql) == 0


# ---- missing vs zero ----------------------------------------------------------------
def test_blank_production_no_longer_carries_a_fake_yield(conn):
    sql = ("SELECT COUNT(*) FROM core.crop_production "
           "WHERE production IS NULL AND yield_reported IS NOT NULL")
    assert scalar(conn, sql) == 0


def test_missing_flag_matches_null_production(conn):
    sql = ("SELECT COUNT(*) FROM core.crop_production "
           "WHERE (production IS NULL) <> is_production_missing")
    assert scalar(conn, sql) == 0


# ---- crops --------------------------------------------------------------------------
def test_each_crop_id_belongs_to_exactly_one_clean_name(conn):
    sql = ("SELECT COUNT(*) FROM (SELECT crop_id FROM core.crop_production "
           "GROUP BY crop_id HAVING COUNT(DISTINCT crop_name_clean) > 1) x")
    assert scalar(conn, sql) == 0


def test_scope_has_15_crops_and_none_are_non_tonnage(conn):
    assert scalar(conn, "SELECT COUNT(DISTINCT crop_name_clean) FROM core.crop_production "
                        "WHERE in_scope") == 15
    assert scalar(conn, "SELECT COUNT(*) FROM core.crop_production "
                        "WHERE in_scope AND unit_basis <> 'tonnes'") == 0
    assert scalar(conn, "SELECT COUNT(*) FROM core.crop_production "
                        "WHERE in_scope AND crop_name_raw LIKE 'Cotton%'") == 0


# ---- annual table ---------------------------------------------------------------------
def test_annual_key_is_unique(conn):
    sql = ("SELECT COUNT(*) FROM (SELECT 1 FROM core.crop_annual "
           "GROUP BY year_start, state_code, district_code, crop_name_raw "
           "HAVING COUNT(*) > 1) x")
    assert scalar(conn, sql) == 0


def test_every_total_row_became_an_annual_total(conn):
    assert scalar(conn, "SELECT COUNT(*) FROM core.crop_annual WHERE annual_source = 'total'") == \
           scalar(conn, "SELECT COUNT(*) FROM core.crop_production WHERE is_season_total")


def test_annual_area_does_not_exceed_the_raw_sum(conn):
    assert scalar(conn, "SELECT SUM(area_annual) FROM core.crop_annual") <= \
           scalar(conn, "SELECT SUM(area) FROM core.crop_production")


def test_annual_yield_equals_production_over_area(conn):
    sql = ("SELECT COUNT(*) FROM core.crop_annual WHERE yield_annual IS NOT NULL "
           "AND ABS(yield_annual - CASE WHEN area_annual > 0 "
           "THEN production_annual / area_annual END) > 0.000001")
    assert scalar(conn, sql) == 0


def test_annual_values_are_not_negative(conn):
    assert scalar(conn, "SELECT COUNT(*) FROM core.crop_annual "
                        "WHERE area_annual < 0 OR production_annual < 0") == 0


def test_season_detail_view_excludes_total_rows(conn):
    assert scalar(conn, "SELECT COUNT(*) FROM core.v_season_detail WHERE is_season_total") == 0


# ---- regression: known values for this dataset --------------------------------------
def test_known_counts_for_this_dataset(conn):
    assert scalar(conn, "SELECT COUNT(*) FROM core.crop_production") == 455359
    assert scalar(conn, "SELECT COUNT(*) FROM core.crop_annual") == 347888
    assert scalar(conn, "SELECT COUNT(*) FROM core.crop_production WHERE is_season_total") == 48044
