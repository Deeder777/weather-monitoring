# Development log

Jahongir Odiljanov – UDE5014CM Assessment 2, "Live Weather Monitoring and Temperature Trend Analysis".
Dates are Asia/Tashkent. Commit hashes refer to https://github.com/Deeder777/weather-monitoring.

**AI assistance.** Claude (Anthropic) was used throughout as a step-by-step guide and code assistant.
Each entry says what Claude provided and what I did myself. I ran every command, checked every output
and made the decisions marked as mine.

## Before collection

|Date|Work|Commit|AI assistance|
|-|-|-|-|
|26 Oct 2026|Approval letter received from Sanjar Bekov; clarifications noted (see `docs/approval.md`).|–|–|
|31 Oct 2026|Created the GitHub repository; set up Git; committed the Checkpoint 1 collector, tests and README unchanged as a baseline.|`9eeda0b`|Claude: guidance on creating the repository and first commit.|
|31 Oct 2026|Collector keeps every raw API response, logs revisions separately and records the retrieval time after the response arrives (letter: preserve originals and revisions). 2 tests added.|`9c6f4f6`|Claude: wrote the change and tests; I ran the tests (5 passing).|
|31 Oct 2026|Collection-window guard (start date, 21 days, 08:00–15:59 Tashkent) and one-batch-per-hour rule. 2 tests added.|`18a51f2`|Claude: wrote the change and tests; I ran them (7 passing).|
|31 Oct 2026|GitHub Actions workflow; database saved on `data` / `data-demo` branches. Demo runs confirmed saving and restoring.|`2cb174f`|Claude: wrote and simulated the workflow; I ran the demo tests on GitHub.|
|31 Oct 2026|Runner pinned to `ubuntu-24.04`; actions updated.|`22b5b77`|Claude: identified the warnings and the fix; I applied it.|
|31 Oct 2026|README and `.gitignore` updated. A duplicate README upload made on the GitHub website was reconciled with a rebase.|`cdb182f`, `979df4f`|Claude: wrote the README; explained the rebase.|
|31 Oct 2026|**Collection start fixed:** `COLLECTION\_START = 2026-11-01`; coordinates and request settings fixed before collection.|`55e30b3`|Claude: recommended the start date; I decided.|

## Collection (1–21 Nov 2026)

|Date|Work|AI assistance|
|-|-|-|
|1 Nov|GitHub's schedule did not fire; 08:00–10:00 missed. Manual live runs saved 11:30 and 12:00. First assessed batch read back from the `data` branch (CP1 evidence).|Claude: diagnosis and read-back commands.|
|1 Nov|Added an external trigger: cron-job.org calls `workflow\_dispatch` at :01 and :06, 08–15 Tashkent, using a token limited to this repository. First error (401) caused by the header misspelled "Authorisation"; fixed. Automatic batches from 13:00.|Claude: step-by-step setup; I created the token and the cron job.|
|13 Nov|15:01 run failed for all cities (TLS handshake timeouts to Open-Meteo); the 15:06 retry saved the batch.|Claude: read the logs with me.|
|15 Nov|11:01 and 11:06 runs failed; my manual run at 11:11 saved the 11:00 batch.|Claude: advised the manual run.|
|17 Nov|11:01 and 11:06 runs failed (timeouts).|Claude: explained the failure pattern.|
|22 Nov|Collection ended (guard refuses after 21 Nov). Workflow disabled, cron-job.org stopped, token revoked.|Claude: shutdown checklist.|

## Analysis and app

|Date|Work|Commit|AI assistance|
|-|-|-|-|
|24 Nov 2026|Final collection check: 492 records, 21 days, 424 pairs; 186 retries, 56 errors. Gap list: 17 missing on-the-hour city-slots. Scripts committed.|`f1c48b9`|Claude: wrote `check\_progress.py` and `list\_gaps.py`; I ran them on the real data.|
|24 Nov 2026|**Analysis plan fixed before any analysis** (date split, assumption checks, 1-day bootstrap blocks, model settings).|`4572df7`|Claude: drafted from my proposal and the letter; I reviewed and accepted it.|
|24 Nov 2026|Five planned queries; 2 tests (9 total).|`415369f`|Claude: wrote queries and tests; I ran them.|
|24 Nov 2026|Five charts (`charts/`).|`2a99fa5`|Claude: wrote `charts.py`; I ran it and checked the charts.|
|24 Nov 2026|Question 2 as pre-registered: +0.11 °C, 95% CI −0.50 to +0.72, p = 0.708 (20 days); complete days +0.39 °C, CI −0.21 to +0.99. 2 tests (11 total).|`1bae24b`|Claude: wrote `compare\_cities.py`; I ran it; we interpreted the result together.|
|24 Nov 2026|Amendment 1 (implementation details for Question 3) and model code, committed before any model was run. 2 tests (13 total).|`1f85264`|Claude: wrote `models.py` and the amendment; I reviewed and committed them.|
|24 Nov 2026|Model settings chosen on development days (three validation windows) and committed. Ridge clearly beat persistence; the random forest failed in window 1 (cannot extrapolate).|`ec378ad`|Claude: explained the validation results.|
|24 Nov 2026|**One-time test on 17–21 Nov:** MAE persistence 1.59 °C, ridge 0.59 °C, forest 0.79 °C.|`65824be`|Claude: helped interpret the results and limitations.|
|25 Nov 2026|Streamlit dashboard (five tabs); display fixes after checking it on the real data. 1 test (14 total).|`26269e3`|Claude: wrote `dashboard.py`; I tested it and reported the display problems.|
|25 Nov 2026|Final README, `docs/approval.md`, offline snapshot with SHA-256.|`272dcad`|Claude: drafted the README and approval notes; I made the snapshot.|
|25 Nov 2026|Clean-clone test: snapshot hash verified, 14 tests pass, 492/21/424 reproduced, dashboard runs offline.|–|Claude: wrote the test procedure; I ran it.|



