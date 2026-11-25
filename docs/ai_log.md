# AI use record (representative, dated)

Tool: **Claude** (Anthropic), used in one long chat in the Claude app from 31 Oct 2026, plus one short
separate chat on 26 Nov 2026. Purpose: step-by-step guidance, code, tests and document drafts.
I ran every command on my laptop, checked every output and made the decisions noted below.
Entries quote my prompts and summarise Claude's outputs. This record was compiled on 26 Nov 2026 from
the chat history; the dates are those of the original messages. Summary per day: `docs/development_log.md`.

| Date | My prompt (short) | Claude's output | How I checked it / what changed |
|---|---|---|---|
| 31 Oct | "Help me set up my existing Python collector on GitHub Actions … one small step at a time." | Steps to create the repository, configure Git, commit the CP1 code unchanged as a baseline. | Created repo; baseline commit `9eeda0b`. |
| 31 Oct | Uploaded `Weather_Checkpoint_1.zip`. | Found the collector kept only a response hash, so revisions would be lost; wrote `raw_responses` + `revision` status and 2 tests. | Ran tests: 5/5. Commit `9c6f4f6`. |
| 31 Oct | (continue) | Window guard, one-batch-per-hour rule, workflow `collect.yml` with `data` branch; simulated the workflow's Git steps before giving it to me. | 7/7 tests; demo runs on GitHub showed `saved` then `duplicate`. `18a51f2`, `2cb174f`. |
| 31 Oct | Screenshot of Node.js 20 / Ubuntu notices. | Pin `ubuntu-24.04`, update actions. Then pointed out I had used *Re-run* (old commit) instead of a new run. | New run #2 on `22b5b77` was clean. |
| 31 Oct | `git push` rejected. | Asked me to inspect before pulling; found my website upload; advised a rebase. | Diff showed only `.gitignore`; rebased; `979df4f`. |
| 1 Nov | Screenshot: no scheduled runs at 11:34. | Diagnosed GitHub schedule not firing; told me to run manually; designed the cron-job.org trigger. | Manual run saved 11:30 batch. |
| 1 Nov | "401 Unauthoriz" | Cause: header name spelled `Authorisation`. | Fixed; test run 201; runs started. |
| 1 Nov | Screenshot of runs #7–#10. | **Wrong:** said the 13:00 batch was probably missed. | Corrected by the data: `show-live` showed 08:00Z (13:00) saved. |
| 13 Nov | Logs of a failed 15:01 run. | TLS handshake timeouts; the 15:06 retry recovered the hour. | Confirmed on 24 Nov by `list_gaps.py` (no 15:00 gap on 13 Nov). |
| 15 Nov | Screenshot: 11:01 and 11:06 failed. | Advised a manual run before 11:15; suggested more retry minutes. | Manual run saved 11:00 (06:00Z). |
| 24 Nov | "421 records?" | Explained 421 was a run number; wrote `check_progress.py`, `list_gaps.py`. | Real result 492 / 21 / 424. **Wrong guess corrected:** Claude guessed the 13 Nov loss was at 15:00; `list_gaps.py` showed 08:00. |
| 24 Nov | "now" (start analysis) | Drafted `docs/analysis_plan.md` from my proposal and the approval letter. | I read it and accepted it; committed before any analysis (`4572df7`). |
| 24 Nov | Ran `compare_cities.py`: scipy missing. | Old `requirements.txt` still in place; gave a command to rewrite it. | 11/11 tests; Q2 result. |
| 24 Nov | `models.py select` output. | Explained the random forest's window-1 failure (no extrapolation). Advised **not** to change the model after seeing validation. | I kept the plan (`ec378ad`), then ran the test once (`65824be`). |
| 25 Nov | Screenshots of the dashboard. | Found two problems in my screenshots: History lines joined 15:00 to 08:00 overnight; failed-attempts bars too small. Fixed both. | Re-checked in the browser; `26269e3`. |
| 25 Nov | Clean-clone output. | Confirmed snapshot hash and 14/14 tests. | Matched my output. |
| 26 Nov | Uploaded the assignment brief. | Found: checkpoint forms vs the letter (to ask the Module Leader); `live` cannot collect after 21 Nov; evidence register, decision records and this log missing. | Opened issues; check mode + tests; documents reviewed and corrected by me before committing. |

## Suggestions rejected or corrected
- Claude's claim that the 13:00 batch on 1 Nov was missed: wrong; disproved by the database.
- Claude's guess about where the 13 Nov loss happened: wrong; corrected by `list_gaps.py`.
- Claude advised against "fixing" the random forest after validation; I agreed and kept the plan.
- Earlier, Claude suggested fetching live data in the dashboard without saving it; replaced on 26 Nov by
  "Collect, save and estimate", because the brief requires new records to be saved and retrieved.
- Claude could not push to GitHub from the chat (permission errors), so I made all commits and the four
  checkpoint tags myself from my laptop.
