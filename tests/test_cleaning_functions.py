"""Unit tests for the Phase 3 cleaning steps (no database needed)."""
import pytest

from src.clean import pipeline as P
from tests.helpers import CROP_MAP, make_raw, row


def run(*rows):
    return P.transform(make_raw(*rows), CROP_MAP)


def test_no_rows_are_dropped():
    out = run(row(1), row(2, season="Rabi"), row(3, season="Total"))
    assert len(out) == 3


def test_year_is_split_into_start_year_and_fiscal_label():
    out = run(row(1, year="1997-1998"))
    assert out.loc[0, "year_start"] == 1997
    assert out.loc[0, "fiscal_year"] == "1997-98"


def test_blank_production_stays_null_and_placeholder_yield_is_reset():
    out = run(row(1, production=None, yld="0"))
    r = out.iloc[0]
    assert bool(r["is_production_missing"]) is True
    assert r["production"] != r["production"]          # NaN
    assert r["yield_reported"] != r["yield_reported"]  # NaN, not 0


def test_zero_production_is_kept_and_flagged_as_zero_not_missing():
    out = run(row(1, production="0", yld="0"))
    r = out.iloc[0]
    assert bool(r["is_zero_production"]) is True
    assert bool(r["is_production_missing"]) is False
    assert r["yield_reported"] == 0


def test_unmapped_crop_name_stops_the_pipeline():
    with pytest.raises(ValueError):
        run(row(1, crop="Mystery Crop"))


def test_blank_district_name_is_recovered_from_its_code():
    out = run(row(1, district="Alpha", dcode="7"), row(2, district=None, dcode="7"))
    assert list(out["district_name"]) == ["Alpha", "Alpha"]


def test_blank_season_stops_the_pipeline_with_a_readable_error():
    with pytest.raises(ValueError):
        run(row(1, season=None))


def test_rounding_in_reported_yield_is_not_a_mismatch():
    # 1 / 368 = 0.002717, reported as 0.003 (3-decimal rounding)
    out = run(row(1, area="368", production="1", yld="0.003"))
    assert bool(out.iloc[0]["is_yield_mismatch"]) is False


def test_a_real_yield_mismatch_is_flagged():
    out = run(row(1, area="100", production="200", yld="5.0"))
    assert bool(out.iloc[0]["is_yield_mismatch"]) is True


def test_non_tonnage_crop_is_marked_and_never_an_outlier():
    rows = [row(i, crop="Coconut", production="800000", yld="8000") for i in range(1, 12)]
    out = run(*rows, row(99, crop="Coconut", production="9000000", yld="90000"))
    assert set(out["unit_basis"]) == {"nuts"}
    assert not out["is_outlier"].any()


def test_outlier_is_flagged_within_its_crop_and_only_that_row():
    rows = [row(i, dcode=str(i)) for i in range(1, 13)]           # 12 normal rows, yield 2.0
    rows.append(row(99, dcode="99", production="20000", yld="200"))  # yield 200
    out = run(*rows)
    assert out["is_outlier"].sum() == 1
    assert bool(out.loc[out["source_id"] == 99, "is_outlier"].iloc[0]) is True


def test_total_season_rows_are_flagged():
    out = run(row(1, season="Kharif"), row(2, season="Total"))
    assert list(out["is_season_total"]) == [False, True]
