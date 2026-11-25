# Checkpoint evidence register

Repository: https://github.com/Deeder777/weather-monitoring, branch `main`. Each checkpoint is tagged
(`cp1`–`cp4`) on the commit below. Approval: written approval from the Module Leader, Sanjar Bekov,
dated 26 October 2026 (see `docs/approval.md`).

**Timing note.** The approval letter said: "Treat Weeks 7–10 as development targets and retain the four
runnable checkpoint commits. The final submission follows the published Week 12 LMS deadline; there are no
separate checkpoint submission deadlines." The letter also required the full 21 days of collection
(1–21 Nov 2026), so CP2–CP4 were completed after collection ended. Commit times below are the real
Git times (Asia/Tashkent). The tags were added on 26 Nov 2026 to existing commits; no commit was changed.
This register was written on 26 Nov 2026 from those commits, the test runs and `docs/development_log.md`.

| Checkpoint | Deadline and full commit hash | Operational component and substantive change | Tests and verifiable results |
|---|---|---|---|
| 1 – Data collection MVP (LO1, LO2) | Week 7 target. `55e30b385917d1cabbbd89befaf5e4f2c180d9ca` (31 Oct 2026 22:40) | Collector `weather.py`: request → validate → save → retrieve, with raw responses, revisions, retrieval time, collection-window guard and GitHub Actions automation. Change from baseline `9eeda0b`: raw-response storage, revision status, guard, workflow. | 7 tests pass. First assessed batch saved on 1 Nov 2026 (source time 06:30Z) and read back from the `data` branch with `show-live`. |
| 2 – Database, reliable collection and data quality (LO2) | Week 8 target. `415369fd8d715fd6c4c6916c0409cf5e20b50f30` (24 Nov 2026 22:16) | 21 days of collection (492 records); progress and gap checks (`check_progress.py`, `list_gaps.py`, commit `f1c48b9`); five stakeholder queries (`queries.py`). | 9 tests pass. 492 records, 21 days, 424 pairs; 186 retries and 56 errors logged; 17 missing slots listed. |
| 3 – Statistical analysis and decision support (LO5) | Week 9 target. `65824bec246cf0e5c9fc7064869c2745863ddf32` (24 Nov 2026 22:51) | Analysis plan fixed first (`4572df7`, Amendment 1 `1f85264`); five charts; Question 2 paired test with checks and bootstrap; Question 3 baseline + ridge + random forest, settings committed (`ec378ad`) before one test. | 13 tests pass. Q2: +0.11 °C, 95% CI −0.50 to +0.72, p = 0.708. Q3 test MAE: persistence 1.59, ridge 0.59, forest 0.79 °C. |
| 4 – Integrated data-producing system (LO1, LO2, LO5) | Week 10 target. `272dcada08f0117899b88781be7c200193553244` (25 Nov 2026 10:44) | Streamlit dashboard (`26269e3`) on the database, queries and model; offline snapshot with SHA-256; README. | 14 tests pass. Clean-clone test on 25 Nov 2026: snapshot hash matched, 14/14 tests, 492/21/424 reproduced, dashboard started. |

Final submission (after CP4): post-window collection check mode, dashboard "Collect, save and estimate",
two end-to-end tests (16 tests), decision records and AI log. See GitHub issues and `docs/decisions.md` (DR-8).

## Value statements

- **CP1.** This component enables a regional weather-information officer to record trustworthy hourly
  conditions for Tashkent, Samarkand and Bukhara by automatically requesting, validating and storing each
  Open-Meteo reading with its source and retrieval time, resulting in a growing dataset where every value
  can be traced to the exact response it came from.
- **CP2.** This component enables a regional weather-information officer to judge whether the dataset is complete enough to use by
  counting records, days and valid one-hour pairs and listing every missing hour, resulting in a verified
  dataset of 492 records (above the approved 450) with all gaps documented.
- **CP3.** This component enables a regional weather-information officer to decide whether the cities differ and whether a simple model
  should replace "it stays the same" by running a pre-registered paired test and a leakage-safe model
  comparison, resulting in the finding that no clear Tashkent–Samarkand difference was detected and that
  ridge regression cut the next-hour error from 1.59 °C to 0.59 °C on the held-out days.
- **CP4.** This component enables a regional weather-information officer to explore the data, check its quality and get a next-hour
  estimate in one local dashboard, resulting in decisions supported by the same database and model without
  running any script by hand.

## Test specifications

Set-up for every checkpoint (Windows PowerShell, Python 3.13):

    git clone https://github.com/Deeder777/weather-monitoring.git
    cd weather-monitoring
    git checkout cpN                      # cp1, cp2, cp3 or cp4
    py -3.13 -m pip install -r requirements.txt   # cp1 has no requirements file: standard library only

### CP1
- **Purpose:** collect, validate, save and retrieve a new record with provenance.
- **Inputs:** Open-Meteo responses (live) or the synthetic fixture (`demo`); invalid responses in tests.
- **Commands:** `py -3.13 -m unittest -v`; `py -3.13 weather.py demo` (twice); `py -3.13 weather.py show-demo`.
- **Expected output:** 7 tests OK; first `demo` saves three records, the second reports `duplicate`;
  `show-demo` lists them.
- **Acceptance criteria:** valid input saved; invalid input rejected and logged; retries recorded; source URL,
  response hash and retrieval time stored; records retrievable.
- **Actual result:** 7/7 tests passed (31 Oct 2026). Live: first assessed batch saved on 1 Nov 2026 and
  retrieved. Note: at this commit `live` only runs inside 1–21 Nov 2026 by design; after that use `demo`
  and the tests, or the final commit's `check` mode.

### CP2
- **Purpose:** reliable collection, data quality and stakeholder queries.
- **Inputs:** the live database from the `data` branch.
- **Commands:** `git fetch origin data`; `git restore --source=origin/data -- weather.sqlite`;
  `py -3.13 -m unittest -v`; `py -3.13 check_progress.py`; `py -3.13 list_gaps.py`; `py -3.13 queries.py`.
- **Expected output:** 9 tests OK; 492 records, 21 days, 424 pairs; 17 missing slots; five query tables.
- **Acceptance criteria:** approved targets met (450 / 20 / 300); duplicates and errors handled and visible;
  pairs require exactly 60 minutes.
- **Actual result:** as expected (24 Nov 2026).

### CP3
- **Purpose:** pre-registered statistical analysis and model comparison.
- **Inputs:** the same database; `docs/analysis_plan.md`.
- **Commands:** database as CP2, then `py -3.13 -m unittest -v`; `py -3.13 charts.py`;
  `py -3.13 compare_cities.py`; `py -3.13 models.py test`.
- **Expected output:** 13 tests OK; charts 1–6; `results/q2_city_comparison.txt` and `results/q3_test.txt`
  with the values in the register.
- **Acceptance criteria:** settings chosen on 1–16 Nov only; test days scored once; assumptions checked;
  uncertainty reported; three robustness checks.
- **Actual result:** as expected (24 Nov 2026). Same numbers on re-run (seed 2026).

### CP4
- **Purpose:** integrated, reproducible end-to-end system.
- **Inputs:** `data/weather_snapshot.sqlite`.
- **Commands:** `Copy-Item data\weather_snapshot.sqlite weather.sqlite`; `py -3.13 -m unittest -v`;
  `py -3.13 -m streamlit run dashboard.py`.
- **Expected output:** 14 tests OK; dashboard with five tabs showing 492 / 21 / 424.
- **Acceptance criteria:** runs from a clean clone without private access; snapshot SHA-256 matches
  `data/SNAPSHOT.md`.
- **Actual result:** as expected in the clean-clone test (25 Nov 2026).

## Known limitations at each checkpoint

- CP1: GitHub's own schedule was untested; on 1 Nov it did not fire (fixed with an external trigger, DR-4).
- CP2: missing data clustered on 13–19 Nov (Open-Meteo timeouts); 17 slots lost.
- CP3: five test days cannot support inference about model differences; persistence is a weak baseline.
- CP4: after 21 Nov the assessed `live` mode refuses to collect, so a new record could not be demonstrated
  from this commit (found on 26 Nov; fixed in the final submission, DR-8).

## Material AI assistance per checkpoint

Claude (Anthropic) wrote most code and documents step by step; I ran every command, checked outputs and made
the decisions. Details and dated examples: `docs/development_log.md` and `docs/ai_log.md`.
