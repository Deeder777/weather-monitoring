# Live Weather Monitoring and Temperature Trend Analysis

UDE5014CM Data Science for Developers – Assessment 2. Author: Jahongir Odiljanov (UDEA).

The collector requests Open-Meteo current conditions for Tashkent, Samarkand and Bukhara,
validates each response, stores it in SQLite and reads it back. Python 3.9 or newer is enough;
no packages, accounts or API keys are needed.

Current stage: collection, storage and automation. The dashboard, analysis and prediction
models are planned work.

## Run locally (Windows PowerShell)

Open PowerShell in this folder.

    py -3.13 -m unittest -v      # 7 automated tests
    py -3.13 weather.py demo     # three synthetic examples into demo.sqlite (run twice: duplicates)
    py -3.13 weather.py show-demo
    py -3.13 weather.py live     # one live batch into weather.sqlite, then exit
    py -3.13 weather.py show-live

`live` only collects inside the approved window (below). Outside it, it prints the reason and
saves nothing.

## Approved collection plan

- Source: Open-Meteo Forecast API, `https://api.open-meteo.com/v1/forecast`, `current` values
  of temperature_2m (°C), relative_humidity_2m (%), wind_speed_10m (km/h), surface_pressure (hPa),
  requested in UTC. City coordinates and request settings are fixed in `weather.py`.
- Window: once per hour, 08:00–15:00 Asia/Tashkent (UTC+5, no daylight saving), for 21 days
  from `COLLECTION_START` in `weather.py`. A late run is accepted until 15:59 and stored with its
  real timestamps.
- One record = one city at one source timestamp. Maximum 504 records; minimum targets are
  450 unique records, at least 20 days with data, and 300 valid same-city pairs exactly one hour
  apart (441 possible). Records are not independent observations.
- Open-Meteo values are model-derived estimates, not independent station measurements.

## Database (SQLite)

- `locations` – the three cities and their fixed coordinates.
- `collection_runs` – one row per attempt: city, `collected_utc` (when the response arrived or
  the attempt failed), request URL, response SHA-256, status and error. Statuses: `saved`,
  `duplicate` (same values already stored), `revision` (same city and source time but different
  values), `retry`, `error`.
- `weather_readings` – accepted readings, unique on (city, source_utc). The first accepted
  values are kept; a revision never replaces them and never counts as a new record.
- `raw_responses` – the exact body of every response received, including rejected ones and
  revisions.

Data rules: demonstration data stays in `demo.sqlite`; only live API records count. Readings are
never invented, backdated, or filled from a historical download. Failed requests and missed
hours stay visible in `collection_runs`.

## Automation with GitHub Actions

The approved proposal described running the collector on a laptop. Collection is automated with
GitHub Actions instead (`.github/workflows/collect.yml`), using the same `weather.py`.

- Schedule: minutes 1, 6 and 11 of every hour 03:00–10:00 UTC (08:00–15:00 Tashkent). GitHub
  does not guarantee scheduled start times, so several triggers are used. Each city is saved at
  most once per Tashkent hour; later triggers only retry a city that is still missing.
- Storage: the runner's disk is temporary, so after each run the workflow commits the database to
  its own branch: `weather.sqlite` on `data` (assessed), `demo.sqlite` on `data-demo` (tests).
  Each commit is a dated record of a run.
- Only one run at a time (concurrency group), so runs cannot overwrite each other.
- If one city fails, the other readings are still saved and the run is marked failed.
- Runner fixed to `ubuntu-24.04` and Python 3.13 for the whole collection period.
- Manual runs: Actions tab → Collect weather → Run workflow (mode `demo` or `live`).

### Download the live database to this laptop

    git fetch origin data
    git restore --source=origin/data -- weather.sqlite
    py -3.13 weather.py show-live

Use `git restore`, not `git show ... > file`: PowerShell redirection would damage the binary file.
`weather.sqlite` is ignored on `main` so the copy is never committed there.

### Starting and ending collection

Assessed collection starts with the commit that sets `COLLECTION_START = date(YYYY, M, D)`.
Day 21 is `COLLECTION_START` + 20 days; after it, `live` refuses to collect. Record the actual
start and end dates and commit hashes in the development log, then disable the workflow
(Actions → Collect weather → ⋯ → Disable workflow).

## Data source and licence

Weather data by Open-Meteo.com (https://open-meteo.com/). API data are licensed under
CC BY 4.0 (https://open-meteo.com/en/licence; licence text https://creativecommons.org/licenses/by/4.0/).
Open-Meteo is free for non-commercial use (https://open-meteo.com/en/terms).
Citation: Zippenfenig, P. (2023). Open-Meteo.com Weather API [Computer software]. Zenodo.
https://doi.org/10.5281/ZENODO.7970649 Transformations: values are stored as returned; responses are
validated (units, timestamp format, plausible ranges) and invalid ones are excluded from
`weather_readings` but kept in `raw_responses`.
