# Live weather monitoring — Checkpoint 1

This first milestone demonstrates one collection cycle: request current conditions, validate the response, save it in SQLite, and read it back. Python 3.9+ is sufficient. No packages, accounts, or keys are needed.

## Start in Windows PowerShell
Extract the ZIP. Open the folder containing weather.py in File Explorer, type powershell in its address bar and press Enter.

    py weather.py demo

The three records are synthetic examples, saved only in demo.sqlite. Repeat the command to see duplicate detection. To read back the saved examples without collecting anything:

    py weather.py show-demo

## After written approval
At a scheduled collection time, run:

    py weather.py live

This requests current conditions separately for Tashkent, Samarkand, and Bukhara. Successful live readings go into weather.sqlite. This command runs once and exits. For the proposed schedule, configure Windows Task Scheduler to run it hourly at 08:00 through 15:00 Tashkent time during the approved 21 days. Keep the computer awake and online. Do not count demonstration data or fill missing hours from an archive.

    py weather.py show-live

The output shows the 12 most recent readings. The database keeps all accepted readings. The pair (city, source time) is unique. Each run records its own collection time, request URL, response hash when available, and status. Network failures are retried up to three times. Invalid responses are logged and excluded.

## Verify and explain
    py -m unittest -v

The tests exercise persistence and duplicates across cities, invalid readings, and recovery from a connection failure. The collector and tests are the starting point for your checkpoint, not a completed final submission. After approval, retain evidence of a genuine live collection and retrieval, commit the working version to your coursework repository, and record the commit and material assistance in your development log.

Source: Open-Meteo Weather Forecast API, https://open-meteo.com/en/docs . Model-derived current conditions are provided by Open-Meteo; see https://open-meteo.com/en/terms for attribution and licence terms. This milestone does not train prediction models.
