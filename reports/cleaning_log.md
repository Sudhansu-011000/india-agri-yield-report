# Cleaning Log

**Project:** Krishi Data Quality Lab: India state-wise crop area, production and yield
**Source file:** `crop-wise-area-production-yield.csv` (455,359 rows, 16 columns, 1997-98 to 2022-23)
**Last updated:** 22 October 2026

Every issue found in the raw data is recorded here with how it was found, what was decided and why.
Rule followed throughout: **flag, don't delete.** The raw file is never edited, and no row is dropped
by the Phase 3 pipeline (455,359 rows in, 455,359 rows out).

## Summary

| # | Issue | Rows affected | Action | Status |
|---|---|---|---|---|
| 1 | Data types and year format | all rows | Convert and split | Done (Phase 3) |
| 2 | Blank production recorded with yield = 0 | 5,009 | NULL + flag | Done (Phase 3) |
| 3 | Zero production (genuine zeros) | 3,997 | Keep + flag | Done (Phase 3) |
| 4 | Crop name variants and typos | 16,409 | Mapping file | Done (Phase 3) |
| 5 | Shared and missing crop codes | 10 codes, 21 blank | Own `crop_id` | Done (Phase 3) |
| 6 | Non-tonnage units labelled as tonnes | 16,428 | Mark `unit_basis` | Done (Phase 3) |
| 7 | Yield vs production / area consistency | 0 real issues | Tested, no action | Done (Phase 3) |
| 8 | Yield outliers | 4,190 | Flag only | Done (Phase 3) |
| 9 | `Total` season overlaps other seasons | 48,044 | Flag now, resolve later | Flagged; fix in Phase 4 |
| 10 | `Whole Year` alongside other seasons | 560 groups | Investigate | Open (Phase 4) |
| 11 | Blank state / district names in staging | see entry | Recover from codes | Done, count to confirm |
| 12 | Administrative boundary changes | n/a | Document | Documented |
| 13 | Duplicate rows | 0 | None needed | Checked |

---

## Issue 1: Data types and year format

- **How found:** Profiling. `crop_code` is stored as a decimal because of blanks; `year` is text like `1997-1998`.
- **Decision:** Convert `area`, `production` and `yield` to numbers. Convert code columns to nullable integers.
  Split `year` into `year_start` (integer) and `fiscal_year` (`1997-98`). Trim spaces from text columns.
- **Why:** Correct types are needed for sorting, filtering and arithmetic. Staging keeps everything as text,
  so nothing was lost or silently changed on load.
- **Rows affected:** All 455,359.
- **Check:** The pipeline counts values lost during numeric conversion. Result: 0 for `area`, `production` and `yield`.
- **Impact:** None on values. Years now sort and filter correctly.

## Issue 2: Blank production recorded with yield = 0

- **How found:** 5,009 rows have no production value, and the source recorded `yield = 0` on every one of them.
- **Decision:** Keep the rows. Leave `production` as NULL. Reset `yield_reported` to NULL.
  Set `is_production_missing = TRUE`.
- **Why:** Area is valid on these rows (no row has a missing area), so deleting them would hide a data gap and
  make the affected crops look better covered than they are. A yield of 0 here is a placeholder, not a
  measurement, and would pull averages down.
- **Rows affected:** 5,009 (all 5,009 placeholder yields reset).
- **Impact:** Excluded from production and yield calculations, and their area must also be excluded from yield
  denominators. About 0.6% of in-scope rows (1,556 of 249,268).

## Issue 3: Zero production with positive area

- **How found:** 3,997 rows have `production = 0` while area is positive.
- **Decision:** Keep the rows and set `is_zero_production = TRUE`. Do not treat as missing.
- **Why:** A zero can be a genuine crop failure or a very small plot rounded down. Deleting these rows would remove the
  worst outcomes and push average yields upward (a bias). Zero and blank mean different things.
- **Rows affected:** 3,997.
- **Impact:** Included in yield calculations. Clusters that look like reporting errors (for example every crop in one
  district-year being zero) should be reviewed in Phase 6.

## Issue 4: Crop name variants and typos

- **How found:** 115 distinct crop names, including variants of the same crop and obvious misspellings.
- **Decision:** Build `mappings/crop_name_map.csv` with the raw name, clean name and product stage.
  Corrections made: `Arcanut (Processed)` and `Atcanut (Raw)` to `Arecanut`; `Cashewnut Raw` and
  `Cashewnut Processed` to `Cashewnut`; `Redish` to `Radish`; `Colocosia` to `Colocasia`; `Pome Granet` to
  `Pomegranate`; `Ribed Guard` to `Ridged Gourd`; `Snak Guard` to `Snake Gourd`; `Sannhamp` to `Sunn Hemp`;
  `Rapeseed &Mustard` to `Rapeseed & Mustard`.
- **Why:** One crop should have one name. The raw name is kept in `crop_name_raw` so every change is traceable.
- **Not done on purpose:** Raw and processed arecanut and cashewnut rows were **not merged** (stage is stored in
  `product_stage`), to avoid double-counting. `Jobster` and `Rajmash Kholar` were left unchanged because the correct
  spelling is uncertain.
- **Rows affected:** 16,409 rows have a changed crop name (111 distinct clean crops remain).
- **Impact:** None of the affected variant crops are among the 15 in-scope crops, except the `Rapeseed & Mustard` spacing fix.

## Issue 5: Shared and missing crop codes

- **How found:** 10 crop codes are shared by different crops (for example code 188 covers Korra, Samai, Varagu and
  Other Cereals; code 1101 covers Cotton(Lint) and Kapas). 21 rows have no crop code
  (`Jute & Mesta`: 20, `Other Dry Fruit`: 1).
- **Decision:** Do not use `crop_code` as a key. Create a project-owned `crop_id` from the clean crop name.
  Keep the original in `crop_code_raw`.
- **Why:** A key must identify one crop; these codes do not.
- **Rows affected:** 10 shared codes; 21 blank codes.
- **Impact:** All joins and groupings use `crop_id`.

## Issue 6: Non-tonnage units labelled as tonnes

- **How found:** The unit columns say `Tonnes` and `Tonnes/Hectare` on every row, but median yields are implausible
  for some crops:
  - Coconut: about 8,094 "tonnes per hectare" (production is almost certainly a count of nuts).
  - Cotton(Lint): about 1.77 (realistic cotton lint yield is far lower; values likely bales).
  - Jute about 9.8, Mesta about 5.0, Jute & Mesta about 8.0 (likely bales).
- **Decision:** Mark these crops with `unit_basis` = `nuts` or `bales` in the crop map. Do not convert.
  Exclude them from cross-crop yield comparisons and outlier detection.
  **Cotton(Lint) was removed from the 15 in-scope crops and replaced by Soyabean.**
- **Why:** No reliable conversion factor is available in the source, and inventing one would be guesswork.
  The classification is inferred from plausibility, not from source metadata, and is documented as such.
- **Rows affected:** 16,428.
- **Impact:** Scope changed (Cotton out, Soyabean in). Coconut is kept as a worked example of a unit mismatch.

## Issue 7: Yield versus production / area

- **How found:** A first test (relative difference above 5%) flagged 181 rows.
- **Investigation:** All 181 are rounding effects. The source rounds yield to 3 decimals, and the largest absolute
  difference in the whole file is 0.0005.
- **Decision:** Recalculate `yield_calc = production / area` for analysis. Flag a mismatch only if the difference
  exceeds both 5% and the rounding tolerance of 0.001. Result: 0 rows flagged.
- **Why:** The reported yields are internally consistent. Reporting "181 errors fixed" would be wrong.
- **Rows affected:** 0 real errors (181 false alarms from the naive test).
- **Impact:** None on values. Documented to show the check was done before assuming an error.

## Issue 8: Yield outliers

- **How found:** Some yields are far beyond plausible values (for example maize with 1,494 and onion with 4,070
  tonnes per hectare), almost certainly entry or unit errors.
- **Decision:** Flag with `is_outlier = TRUE` when `yield_calc` exceeds Q3 + 3 x IQR within the same crop. Applied only
  to tonnage crops with positive yield. Nothing is deleted.
- **Why:** Outlier handling is an analysis decision. Flags keep the choice visible and reversible. The fence is per
  crop because a normal sugarcane yield would be an extreme outlier for a pulse.
- **Rows affected:** 4,190. The earlier baseline profile counted about 4,375 because it also included non-tonnage
  crops and zero yields in the quartiles.
- **Impact:** Decide in Phase 6 whether to exclude, cap or keep, and report sensitivity of the results.

## Issue 9: `Total` season overlaps other seasons

- **How found:** 48,044 rows have `season = Total`, and for the same year, district and crop the individual seasons
  are also present. Summing everything double-counts.
- **Decision (Phase 3):** Flag with `is_season_total = TRUE`; keep all rows.
- **Decision (Phase 4):** Build one annual figure per year, district and crop: use `Total` if present, otherwise
  `Whole Year`, otherwise the sum of individual seasons. Compare `Total` with the sum of its seasons and report the
  mismatch rate.
- **Why:** `Total` cannot simply be used alone, because it is almost absent for some crops (Wheat has `Total` on only
  32 rows, since it is nearly all Rabi).
- **Rows affected:** 48,044.
- **Impact:** Until Phase 4 is done, never sum area or production across all rows.

## Issue 10: `Whole Year` alongside other seasons

- **How found:** About 560 year-district-crop groups contain `Whole Year` and also one or more individual seasons.
- **Decision:** Open. Inspect these groups in Phase 4 to decide whether `Whole Year` is already a total for them.
- **Why:** Treating it wrongly would double-count or under-count those groups.
- **Rows affected:** About 560 groups.

## Issue 11: Blank state or district names in staging

- **How found:** The Phase 3 load into `core.crop_production` failed with a NOT NULL violation on `district_name`
  for source row `id = 10` (state code 28, district code 502, crop Groundnut, season Total). In the reference CSV
  this row has the district name Ananthapuramu, so the blank was already present in the project's staging table
  or local copy of the file.
- **Decision:** Recover a blank state or district name from other rows with the same code (state code, or state code
  plus district code). If a code never appears with a name, use `Unknown`. A check stops the pipeline with a readable
  message if `year`, `crop_name` or `season` is blank.
- **Why:** State and district codes map 1:1 to names in this dataset (0 conflicts found), so recovery is lossless.
  The NOT NULL rule is kept so the core table stays clean.
- **Rows affected:** `<fill in from the console line "district_name blank in staging">`
  and `<fill in from "district_name recovered from code">`.
- **Impact:** None expected after recovery. If any rows became `Unknown`, list them here.

## Issue 12: Administrative boundary changes

- **How found:** Profiling of districts and states by year.
- **Findings:**
  - The number of districts grows from 512 (1997-98) to 736 (2022-23) because new districts were created.
  - Telangana appears from 1997-98, back-cast after its 2014 split from Andhra Pradesh.
  - Ladakh appears before it became a separate Union Territory in 2019.
  - Dadra & Nagar Haveli and Daman & Diu is a 2020 merger, shown as one entity throughout.
- **Decision:** No data change. District-level analysis is limited to 2010-11 onward, and state-level rankings
  require at least 15 years of data per crop.
- **Why:** Comparing district counts or district series across boundary changes would mislead.

## Issue 13: Duplicate rows

- **How found:** Profiling.
- **Result:** 0 exact duplicates (ignoring `id`) and 0 duplicate keys on year, state, district, crop and season.
- **Decision:** No action.

---

## Appendix: Pipeline and setup problems encountered

| Problem | Cause | Resolution |
|---|---|---|
| `mkdir -p` failed in PowerShell | Bash syntax used on Windows | Used `New-Item -ItemType Directory -Force -Path ...` |
| Port conflicts with Docker | Local PostgreSQL servers already use ports 5432 and 5433 | Used the existing PostgreSQL 17 server (port 5433) directly, no Docker |
| `ModuleNotFoundError: No module named 'src'` | Script run directly instead of as a module | Run with `python -m src.<module>` from the project root |
| `NotNullViolation` on `district_name` | Blank district name in staging row `id = 10` | See Issue 11 |

## Before and after tracking

Counts are saved by the pipeline to `reports/cleaning_step_counts.csv` and the baseline to
`reports/baseline_quality.csv`. The before/after comparison table is completed in Phase 5.
