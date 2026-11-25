# Decision and defect records

**How this file was made.** DR-1 to DR-7 were written on 26 Nov 2026 from the dated commits, the
`data` branch history and `docs/development_log.md`. They were not recorded as GitHub issues at the time;
they are listed here so each decision is traceable to its evidence, not to simulate earlier records.
DR-8 onwards were opened as GitHub issues when the work started.

## DR-1 – Move collection from the laptop to GitHub Actions (decision, 31 Oct 2026)
- **Context:** the approved proposal ran the collector on my laptop. A laptop that sleeps or is off would
  miss hours; the targets (450 records, 300 pairs) left little room for gaps.
- **Decision:** run the same `weather.py` on GitHub Actions; commit the database to a separate `data`
  branch after each run; test first with demo data on `data-demo`.
- **Alternatives:** Windows Task Scheduler (rejected: laptop must stay on); a paid cloud server (rejected:
  cost, and the project must run without private services).
- **Acceptance criteria:** a run restores the saved database, adds readings and saves it again; a second
  demo run reports `duplicate`.
- **Evidence:** `2cb174f`, `22b5b77`; demo runs #1 (attempts 1–2) and #2 on 31 Oct 2026.
- **Verification:** second demo run printed `duplicate` for all cities. **Status:** done.

## DR-2 – Keep every raw response and record revisions separately (decision, 31 Oct 2026)
- **Context:** the approval letter asked to preserve original responses and later revisions; the
  Checkpoint 1 collector kept only a hash, and a changed value would have been lost as a "duplicate".
- **Decision:** `raw_responses` table; status `revision` when the same city and source time return
  different values; keep the first reading. Record retrieval time after the response arrives.
- **Acceptance criteria:** raw body stored for saved, duplicate and rejected responses; revision logged and
  original kept. **Evidence:** `9c6f4f6`, tests `test_raw_responses_are_kept`,
  `test_revision_is_logged_and_original_reading_kept`. **Status:** done.

## DR-3 – Collection-window guard and one batch per hour (decision, 31 Oct 2026)
- **Context:** manual, repeated or late runs must not add records outside the approved plan.
- **Decision:** `live` refuses outside 1–21 Nov 2026, 08:00–15:59 Tashkent; each city saved at most once
  per hour; a failed city can be retried within the hour.
- **Evidence:** `18a51f2`; tests `test_collection_window`, `test_one_batch_per_hour_keeps_partial_success`.
  **Status:** done. (Side effect found later: DR-8.)

## DR-4 – External trigger after GitHub's schedule did not fire (defect and decision, 1 Nov 2026)
- **Defect:** no scheduled run appeared on day 1; the 08:00–10:00 slots were lost.
- **Decision:** cron-job.org calls GitHub's `workflow_dispatch` API at minutes 1 and 6 of each hour,
  08–15 Tashkent, with a fine-grained token limited to starting workflows in this repository; GitHub's
  schedule kept as a backup. The token was revoked after collection.
- **Evidence:** `data` branch commit times; `collection_runs.collected_utc` from 13:01 on 1 Nov 2026;
  README "Triggers". **Verification:** automatic batches saved at 13:01, 14:01 and 15:01 on day 1.
  **Status:** done.

## DR-5 – Trigger failed with HTTP 401 (defect, 1 Nov 2026)
- **Cause:** the phone keyboard changed the header name `Authorization` to `Authorisation`.
- **Fix:** corrected the header; test run returned HTTP 201 and the workflow started.
- **Evidence:** cron-job.org history; workflow runs #4–#6 on 1 Nov 2026. **Status:** closed.

## DR-6 – Open-Meteo connection timeouts (defect, 13–19 Nov 2026)
- **Observed:** TLS handshake timeouts for all cities in some runs (186 retries, 56 errors in total).
- **Response:** the :06 retry trigger and manual runs recovered most hours (for example 15:00 on 13 Nov,
  11:00 on 15 Nov). Not fixed in code: the failures were outside the system. Retries and errors stay logged.
- **Evidence:** `collection_runs`; `list_gaps.py` output (17 missing slots); chart 5. **Status:** accepted
  limitation, discussed in the report.

## DR-7 – Pre-registered analysis and Amendment 1 (decision, 24 Nov 2026)
- **Decision:** fix the date split, assumption checks, bootstrap block length and model settings before
  any analysis (`4572df7`); add implementation details for Question 3 before any model was run
  (`1f85264`); commit model settings (`ec378ad`) before the one-time test (`65824be`).
- **Rejected alternative:** changing the random forest after it failed validation window 1 (it cannot
  extrapolate below its training range). Rejected because the plan fixed the models; reported as a
  limitation instead.
- **Verification:** `models.py test` refuses to run until the settings file is committed
  (`test_models.py` covers the date split). **Status:** done.

## DR-8 – A new record cannot be collected after the window (defect, 26 Nov 2026)
- **Found:** while checking the final submission against the brief ("a new record can be collected,
  saved and retrieved"), `weather.py live` refuses after 21 Nov because of DR-3.
- **Fix:** `weather.py check` collects into `post_collection.sqlite` with the same validation and
  provenance code, at any time; the assessed `live` mode and data are unchanged. Dashboard button
  "Collect, save and estimate". Two end-to-end tests.
- **Acceptance criteria:** `check` saves three cities with source URL, retrieval time and raw response;
  the new record is retrievable by query 1 and usable as model input; `weather.sqlite` is not touched.
- **Evidence:** GitHub issue (see issue list), fixing commit, `test_end_to_end.py`. **Status:** closed by
  the fixing commit.
