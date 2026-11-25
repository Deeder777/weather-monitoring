# Approval and implementation of the clarifications

Approval letter from the Module Leader, Sanjar Bekov, received on **\[26.10.2026]**.
The project "Live Weather Monitoring and Temperature Trend Analysis" was approved for LO1, LO2 and LO5,
with a minimum of 450 unique city-hour records across at least 20 days, including 300 valid one-hour
prediction pairs, for a limited pilot study. The number of records must not be presented as the number
of independent observations. The clarifications did not require another approval submission.

|Clarification in the letter|How it was implemented|Evidence|
|-|-|-|
|Fix coordinates and request settings before collection|Fixed in `weather.py`; collection window set in one commit|`55e30b3`|
|Store source-valid and retrieval timestamps separately|`weather\_readings.source\_utc` and `collection\_runs.collected\_utc` (time the response arrived)|`9c6f4f6`|
|Build pairs from returned timestamps exactly one hour apart|`queries.py` query 5 and `models.load\_pairs` require exactly 60 minutes; tested|`test\_queries.py`, `test\_models.py`|
|Preserve original responses and revisions separately|`raw\_responses` keeps every body; a changed value is logged as `revision` and never overwrites the first|`9c6f4f6`|
|At most 7 pairs per city per day, 441 over 21 days|424 valid pairs reached|`check\_progress.py`|
|Choose features, preprocessing and settings on development days only; keep the final five days untouched|Validation windows inside 1–16 Nov; settings committed before the test; `models.py test` refuses otherwise|`ec378ad`, `65824be`|
|Report errors by day and city; describe results as exploratory|`results/q3\_test.txt`|`65824be`|
|Specify assumption checks and primary bootstrap block length in advance|`docs/analysis\_plan.md`|`4572df7`|
|Where days cannot support reliable inference, report observed differences|No significance claim from the five test days|`docs/analysis\_plan.md`|
|Offline snapshot acceptable; keep demo and manual data separate|`data/weather\_snapshot.sqlite`; demo data only in `demo.sqlite`; the dashboard's live check never saves|`data/SNAPSHOT.md`|
|Record actual collection dates|1–21 Nov 2026, from the first assessed batch in the database|README|
|Retain five queries, five visualisations, three robustness checks, eight meaningful tests, setup instructions|5 queries, 6 charts, 3 robustness checks, 14 tests, README|this repository|

Change not covered by the letter: collection ran on GitHub Actions instead of the laptop described in the
proposal, triggered by cron-job.org after GitHub's own schedule did not fire on day 1. This is documented
in the README and the development log.

