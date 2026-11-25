# Live Weather Monitoring and Temperature Trend Analysis

UDE5014CM Data Science for Developers – Assessment 2. Author: Jahongir Odiljanov (UDEA).

An automated collector requested Open-Meteo current conditions for **Tashkent, Samarkand and Bukhara**
every hour from 08:00 to 15:00 (Asia/Tashkent) for 21 days, 1–21 November 2026. Each response was
validated and stored in SQLite. The project then compares the cities statistically and tests whether a
model can predict the temperature Open-Meteo publishes one hour later better than "it stays the same".
A local Streamlit dashboard shows the data, its quality and the model.

All results are **exploratory**. Records are repeated hourly readings of three cities, not independent
observations, and conclusions apply only to these cities, dates and daytime hours.

## Results in brief

| Item | Result | Target |
|---|---|---|
| Unique records | 492 of 504 possible | at least 450 (90% target 454) |
| Days with data | 21 | at least 20 |
| Valid one-hour pairs | 424 of 441 possible | at least 300 |

- **Question 1** (variation): Bukhara was warmest in the afternoon and windiest; Tashkent calmest.
  Temperature rose by about 8 °C between 08:00 and 14:00 on average. A cold change came around 10–11 Nov.
- **Question 2** (Tashkent vs Samarkand, 20 qualifying days): mean daily difference +0.11 °C,
  95% CI −0.50 to +0.72 °C, paired t-test p = 0.708. No clear difference was found; this does not show
  that there is none. Complete days only (17): +0.39 °C, CI −0.21 to +0.99.
- **Question 3** (next-hour temperature, one-time test on 17–21 Nov, 103 pairs): MAE persistence 1.59 °C,
  ridge regression 0.59 °C, random forest 0.79 °C. Persistence ignores daytime warming, so it is a weak
  baseline; with five test days no significance claim is made.

Full outputs: `results/`. Charts: `charts/`.

## Quick start (offline, Windows PowerShell)

Python 3.11 or newer; tested with Python 3.13 (`py -3.13`). Internet is needed only to install the packages
once and for fresh API data.

    git clone https://github.com/Deeder777/weather-monitoring.git
    cd weather-monitoring
    py -3.13 -m pip install -r requirements.txt
    Copy-Item data\weather_snapshot.sqlite weather.sqlite
    py -3.13 -m unittest -v
    py -3.13 -m streamlit run dashboard.py

`data/weather_snapshot.sqlite` is a copy of the final live database (see *Offline snapshot* below).
`weather.sqlite` is ignored by Git, so the copy is never committed. The dashboard also opens the snapshot
directly if `weather.sqlite` is missing.

## Commands

| Command | What it does |
|---|---|
| `py -3.13 -m unittest -v` | 14 automated tests (collector, queries, statistics, models, dashboard) |
| `py -3.13 queries.py` | the five planned database queries (`queries.py 3` for one) |
| `py -3.13 check_progress.py` | records, days and pairs against the targets, per day |
| `py -3.13 list_gaps.py` | every missing on-the-hour slot and every off-the-hour reading |
| `py -3.13 charts.py` | charts 1–5 into `charts/` |
| `py -3.13 compare_cities.py` | Question 2 with the planned checks; writes `results/q2_city_comparison.txt` and chart 6 |
| `py -3.13 models.py select` | Question 3 settings from development days only; writes `results/q3_selection.json` |
| `py -3.13 models.py test` | one-time test on 17–21 Nov; refuses to run until the selection is committed |
| `py -3.13 -m streamlit run dashboard.py` | local dashboard at http://localhost:8501 |
| `py -3.13 weather.py demo` / `show-demo` | three synthetic examples in `demo.sqlite` (never used in analysis) |
| `py -3.13 weather.py live` / `show-live` | one live batch; refuses outside the approved collection window |

Re-running `models.py test` gives the same numbers (fixed seed 2026) and adds another row to
`results/model_runs.sqlite`; the reported evaluation is the first run, commit `65824be`.

## Repository layout

    weather.py            collector: request, validate, store, retrieve
    queries.py            the five planned queries
    charts.py             charts 1–5
    compare_cities.py     Question 2
    models.py             Question 3 (select / test)
    dashboard.py          Streamlit dashboard
    check_progress.py, list_gaps.py   collection checks
    test_*.py             automated tests
    .github/workflows/collect.yml     GitHub Actions collector
    data/weather_snapshot.sqlite      offline copy of the final live database
    docs/analysis_plan.md fixed before analysis (with Amendment 1)
    docs/approval.md      approval and how each clarification was implemented
    results/              text results, model settings, model_runs table
    charts/               PNG charts for the report

## Data collection

- **Source:** Open-Meteo Forecast API, `https://api.open-meteo.com/v1/forecast`, `current` values of
  temperature_2m (°C), relative_humidity_2m (%), wind_speed_10m (km/h) and surface_pressure (hPa),
  requested in UTC. Coordinates and request settings are fixed in `weather.py`.
  Values are model-derived estimates, not independent station measurements.
- **Window:** 08:00–15:00 Asia/Tashkent (UTC+5, no daylight saving), 1–21 Nov 2026. Set in the commit that
  started collection (`55e30b3`). A late run is accepted until 15:59 and stored with its real timestamps.
- **Automation:** the approved proposal described running the collector on a laptop; collection was moved
  to GitHub Actions (`.github/workflows/collect.yml`), running the same `weather.py`. After each run the
  database was committed to the `data` branch (`demo.sqlite` to `data-demo` for tests). One run at a time
  (concurrency group). If one city failed, the others were still saved.
- **Triggers:** GitHub's own schedule did not fire on day 1 (08:00–10:00 missed; 11:00 collected late, at
  11:30, by a manual run). From 13:00 on day 1 an external scheduler (cron-job.org) started the workflow
  through GitHub's `workflow_dispatch` API at minutes 1 and 6 of each collection hour, with GitHub's
  schedule as a backup. The collector saves each city at most once per Tashkent hour, so extra triggers
  only retry missing cities. The trigger used a fine-grained token limited to starting workflows in this
  repository; it was revoked after collection.
- **Failures:** 186 retries and 56 errors were logged, mostly TLS handshake timeouts to Open-Meteo on
  13–19 Nov. Lost: 17 on-the-hour city-slots (12 on 1 Nov; 13 Nov 08:00 Tashkent and Samarkand;
  14 Nov 08:00 Tashkent; 18 Nov 15:00 Tashkent and Samarkand, saved late at 15:15).
  Missing hours are never filled from a historical download or invented.

## Database (SQLite)

- `locations` – the three cities and their fixed coordinates.
- `collection_runs` – one row per attempt: city, `collected_utc` (when the response arrived or the attempt
  failed), request URL, response SHA-256, status and error. Statuses: `saved`, `duplicate`, `revision`,
  `retry`, `error`.
- `weather_readings` – accepted readings, unique on (city, source_utc). The first accepted values are kept.
- `raw_responses` – the exact body of every response received, including rejected ones and revisions.
- `model_runs` (in `results/model_runs.sqlite`) – each test evaluation: model, setting, days, MAE, RMSE,
  mean error.

## Offline snapshot

`data/weather_snapshot.sqlite` is an unmodified copy of `weather.sqlite` from the `data` branch, taken
after collection ended. Its SHA-256 and the `data` commit it came from are recorded in
`data/SNAPSHOT.md`. To use the live database instead:

    git fetch origin data
    git restore --source=origin/data -- weather.sqlite

## Analysis method

`docs/analysis_plan.md` was committed before any analysis (`4572df7`); Amendment 1 (implementation details
for Question 3) was added before any model was run. Model settings were chosen on 1–16 Nov with three
forward validation windows and committed (`ec378ad`) before the final five days were scored once
(`65824be`).

| Evidence | Commit |
|---|---|
| Checkpoint 1 baseline | `9eeda0b` |
| Collection start date fixed | `55e30b3` |
| Analysis plan fixed | `4572df7` |
| Five queries | `415369f` |
| Charts | `2a99fa5` |
| Question 2 | `1bae24b` |
| Question 3 settings committed | `ec378ad` |
| Question 3 one-time test | `65824be` |
| Dashboard | `26269e3` |

## Limitations

- 21 days in November, daytime hours only, three cities; records are not independent.
- The outcome is the value Open-Meteo publishes an hour later, a model estimate, not a measurement.
- Missing data was not random: the gaps on 13–18 Nov fell during the colder spell.
- Five test days cannot support inference about model differences.
- Persistence is a weak baseline for daytime hours; a "current temperature + typical hourly change"
  baseline would be a fairer comparison.
- The random forest failed in the first validation window (it cannot predict outside its training range).

## Data source and licence

Weather data by Open-Meteo.com (https://open-meteo.com/). API data are licensed under CC BY 4.0
(https://open-meteo.com/en/licence; licence text https://creativecommons.org/licenses/by/4.0/).
Open-Meteo is free for non-commercial use (https://open-meteo.com/en/terms).
Changes made: values are stored as returned; responses are validated (units, timestamp format, plausible
ranges) and invalid ones are excluded from `weather_readings` but kept in `raw_responses`; derived tables
and statistics are computed from the stored values.
Citation: Zippenfenig, P. (2023). Open-Meteo.com Weather API [Computer software]. Zenodo.
https://doi.org/10.5281/ZENODO.7970649

## AI assistance

Material AI assistance (Claude, Anthropic) is recorded with dates in the development log.
