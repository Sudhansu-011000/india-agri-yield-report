Scope of the project
Project title: Krishi Data Quality Lab: Cleaning and Analyzing India’s State-wise Crop Yield Data (1997-98 to 2022-23)

1. Objective and audience
Objective: Turn a raw government crop file into a trustworthy dataset and a dashboard, and show with measured before/after metrics what the cleaning changed.
Primary audience: Hiring managers and interviewers, who care about how I handled messy data.
Secondary (imagined) audience: A state agriculture planner who wants to compare yield trends across states.
What I’m claiming: “I can find the problems hidden in a real government file and fix them.
2. Time window
Full range, 1997-98 to 2022-23 (26 years), for state-level analysis. Every state file in the data has 20 to 26 years, so long-run trends are well supported.
District-level analysis only from 2010-11 to 2022-23. The number of districts grows from 512 (1997-98) to 736 (2022-23) because new districts were created, and comparing district counts across that whole span would mislead.
Why not shorten everything? The 26-year span is one of the dataset’s strengths, and CAGR(Compound Annual Growth Rate) and volatility questions need it.
3. Geography and grain
Main grain: state × crop × year × season. I’ll aggregate districts up to state, and the pipeline starts from district rows.
Coverage: All 34 states and UTs stay in the cleaned data, but rankings only include a state if it has at least 15 years of data for that crop. Tiny entries like Chandigarh (133 rows) and Ladakh (343 rows) are kept, but excluded from rankings so they don’t distort results.
District drill-down: 4 states only. Uttar Pradesh (75 districts, the most rows), Madhya Pradesh, Karnataka and Bihar. They give large, varied samples across regions.
Documented geography caveats:
Telangana appears from 1997-98 (back-cast after the 2014 split from Andhra Pradesh).
Ladakh appears before it became a separate UT in 2019.
Dadra & Nagar Haveli and Daman & Diu is a 2020 merger, shown as one entity throughout.
4. Crops (15, not 115)
I’ll use the major crops that have complete 26-year coverage and low missing-production rates (under 2%):
Group	Crops
Cereals (5)	Rice, Wheat, Maize, Jowar, Bajra
Pulses (4)	Gram, Arhar/Tur, Moong, Urad
Oilseeds (2)	Groundnut, Rapeseed & Mustard
Cash crops (2)	Sugarcane, Soyabean
Vegetables (2)	Potato, Onion
“Cotton(Lint) removed after unit check: median yield 1.77 ‘tonnes/ha’ implies values are likely bales, not tonnes.”
Why these: They cover the main food and cash crop groups, each appears in 24 to 33 states, and the data is dense enough for trends.
Excluded on purpose:
	Coconut: production is recorded in nuts but labeled “Tonnes”, so yield comparisons would be meaningless. I’ll use it as a worked example in my unit-mismatch 	documentation, but keep it out of the dashboard.
	“Other ...” buckets (Other Cereals, Other Oilseeds, etc.): they mix unrelated crops.
Duplicated/variant crops (Arecanut/Arcanut/Atcanut, Cashewnut variants): handled in the cleaning pipeline, not analyzed.
One check I need to do: confirm Cotton(Lint) values are plausible in tonnes before trusting it. If not, I’ll drop it and the project still works.

5. Season handling
This is the trickiest scope decision, because the Total season overlaps the individual seasons.
Why I can’t just use Total: It exists for only about 48,000 rows, and for some crops it’s almost absent (Wheat has Total in just 32 rows, because wheat is nearly all Rabi).
My annual rule, applied per (year, district, crop):
	Use Total if present.
	Otherwise use Whole Year if present.
	Otherwise sum the individual seasons.
Quality check: Where Total exists, I’ll compare it with the sum of its seasons and report the mismatch rate as a data quality metric.
Two analysis levels:
Headline KPIs and rankings use the annual basis.
A season-detail page (Kharif vs Rabi) uses individual seasons only, never mixed with Total.

6. Data cleaning scope (the core of the project)
In scope, from the issues I found:
Missing production (5,009 rows, where the source wrote yield = 0): keep as NULL, add a flag, no imputation.
Genuine zero production (3,997 rows) vs missing: separate them.
Total double-counting: handled by the annual rule above.
Crop name and code problems: a mapping file, plus my own crop_id because 10 crop codes are shared by different crops.
Unit plausibility checks (the coconut case).
Yield reconciliation (181 rows where yield ≠ production ÷ area).
Per-crop outlier flagging (about 4,375 rows). I flag them, and decide case by case whether to exclude.
Geography change documentation (Telangana, Ladakh, district growth).
Data type fixes (crop_code, the year split).
Not in scope: imputing missing production, correcting individual values by guesswork, or re-sourcing data from other portals.

7. Analysis scope
Main questions: I’ll answer the 20 questions listed earlier, adjusted to the 15 crops. Roughly:
5 beginner (rankings, totals, coverage)
6 intermediate (state vs national average, area-vs-yield-driven growth)
7 advanced (CAGR, volatility, outliers, imputation sensitivity)
2 on data quality improvement
Core metrics: total production, area, yield (recalculated as production ÷ area), YoY change, CAGR, coefficient of variation.
Weighted, not averaged, yield: State and national yields will be total production ÷ total area, never an average of district yields.

8. Technical scope
Staging: PostgreSQL via Docker (raw staging as text, then typed core tables, then views).
Cleaning: Python (pandas, plus pytest for validation rules).
Visualization: Tableau dashboard (4 pages) and Streamlit app (5 pages).
Reproducibility: One make or script run reproduces everything from the raw CSV.

9. Deliverables and “done” criteria
Deliverable	                Done when
Clean dataset + flags	Passes all validation tests; every changed row is traceable
Cleaning log	                Each issue has: detection query, decision, justification, rows affected
Before/after quality report	Same metrics measured before and after, in one table
PostgreSQL schema	        Runs from scratch with one command
Tableau dashboard	        4 pages, state filter, crop filter and year slider all working
Streamlit app	        5 pages, including a Data Quality Lab page, deployed publicly
PDF documentation	        Covers sources, method, findings, limitations
GitHub repo	                Clean structure, README with screenshots, requirements.txt

10. Out of scope (kept on a “future work” list)
Prediction or forecasting models (not a fit for this project’s purpose)
External data (rainfall, irrigation, fertilizer, MSP prices)
All 115 crops and all 737 districts in the dashboard
Real-time or automated data refresh
Causal claims (why yields rose); I’ll describe trends, not explain them
crops reported in non-tonnage units (coconut, cotton, jute, mesta).