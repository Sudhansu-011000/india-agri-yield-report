"""Unit tests for the Phase 4 annual rule (no database needed)."""
from src.clean import annual as A
from src.clean import pipeline as P
from tests.helpers import CROP_MAP, make_raw, row


def annual_of(*rows):
    core = P.transform(make_raw(*rows), CROP_MAP)
    return core, A.build_annual(core)


def test_total_row_is_used_when_present():
    _, a = annual_of(row(1, "Kharif", "100", "200"), row(2, "Rabi", "50", "60"),
                     row(3, "Total", "150", "260"))
    r = a.iloc[0]
    assert len(a) == 1
    assert r["annual_source"] == "total"
    assert r["area_annual"] == 150 and r["production_annual"] == 260
    assert r["n_source_rows"] == 3


def test_rows_are_summed_when_there_is_no_total_and_whole_year_counts_as_a_season():
    _, a = annual_of(row(1, "Kharif", "100", "200"), row(2, "Whole Year", "30", "40"))
    r = a.iloc[0]
    assert r["annual_source"] == "sum_of_rows"
    assert r["area_annual"] == 130 and r["production_annual"] == 240
    assert bool(r["has_whole_year"]) is True


def test_one_blank_component_production_makes_annual_production_null_not_understated():
    _, a = annual_of(row(1, "Kharif", "100", "200"), row(2, "Rabi", "50", None, "0"))
    r = a.iloc[0]
    assert r["area_annual"] == 150
    assert r["production_annual"] != r["production_annual"]   # NaN
    assert bool(r["is_production_missing"]) is True


def test_total_that_disagrees_with_its_rows_is_flagged_but_still_used():
    _, a = annual_of(row(1, "Kharif", "100", "200"), row(2, "Total", "500", "900"))
    r = a.iloc[0]
    assert bool(r["is_total_mismatch"]) is True
    assert r["annual_source"] == "total" and r["area_annual"] == 500


def test_total_that_agrees_with_its_rows_is_not_flagged():
    _, a = annual_of(row(1, "Kharif", "100", "200"), row(2, "Rabi", "50", "60"),
                     row(3, "Total", "150", "260"))
    assert bool(a.iloc[0]["is_total_mismatch"]) is False


def test_exactly_one_annual_row_per_year_district_crop():
    core, a = annual_of(
        row(1, "Kharif", dcode="1"), row(2, "Total", "100", "200", dcode="1"),
        row(3, "Kharif", dcode="2"), row(4, "Rabi", dcode="2"),
        row(5, "Kharif", dcode="3", year="2011-2012"),
    )
    assert len(a) == 3
    assert not a.duplicated(A.KEY).any()


def test_summing_all_rows_would_double_count_but_the_annual_table_does_not():
    core, a = annual_of(row(1, "Kharif", "100", "200"), row(2, "Rabi", "50", "60"),
                        row(3, "Total", "150", "260"))
    assert core["area"].sum() == 300          # naive sum is double
    assert a["area_annual"].sum() == 150      # annual is correct


def test_annual_yield_is_total_production_over_total_area_not_an_average_of_yields():
    _, a = annual_of(row(1, "Kharif", "100", "100", "1.0"), row(2, "Rabi", "300", "900", "3.0"))
    assert a.iloc[0]["yield_annual"] == 2.5   # 1000 / 400, the mean of yields would be 2.0
