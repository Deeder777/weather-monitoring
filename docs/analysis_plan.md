# Analysis plan (fixed before analysis)

Project: Live Weather Monitoring and Temperature Trend Analysis (UDE5014CM, Assessment 2).
Written after collection ended and **before any analysis or model was run**. The commit that adds
this file is the evidence of that order. Any later change is added as a dated amendment at the end
and explained in the report; the original text is not edited.

## 1. Data

- Source: `weather_readings` in `weather.sqlite` on the `data` branch, collected 1–21 Nov 2026,
  08:00–15:00 Asia/Tashkent. Final count: 492 records, 21 days, 424 valid one-hour pairs.
- Dates are Tashkent dates. Day 1 = 1 Nov 2026.
- Records are repeated hourly readings of three cities. They are **not independent
  observations**, and results are described as exploratory.
- Conclusions apply only to these three cities, these dates and these daytime hours.
- Manually entered or demonstration records are never used in any analysis.

## 2. Date split (prediction models only)

| Part | Days | Use |
|---|---|---|
| Development | 1–16 Nov | features, preprocessing, model settings |
| Test | 17–21 Nov (final five days) | evaluated once, at the end |

- All three cities use the same split.
- A prediction pair is two readings of the same city with source times exactly 60 minutes apart.
  All pairs fall within one day (08:00→09:00 … 14:00→15:00), so splitting by whole days means no
  pair crosses a split.
- Forward validation windows inside the development days:

| Window | Train on | Validate on |
|---|---|---|
| 1 | 1–10 Nov | 11–12 Nov |
| 2 | 1–12 Nov | 13–14 Nov |
| 3 | 1–14 Nov | 15–16 Nov |

- The test days are not opened (no summaries, no plots, no model scores) until the models are fixed.
  The final models are refitted on 1–16 Nov and scored once on 17–21 Nov.

## 3. Question 1 – variation across cities

Descriptive only: mean, standard deviation, minimum, maximum and hourly profile of temperature,
humidity and wind per city. Uses all 21 days, because no model is selected from it.

## 4. Question 2 – Tashkent vs Samarkand daytime temperature

- Match readings at the same source time. A day qualifies if it has **at least 6 matched hours**.
- For each qualifying day, compute one paired difference: mean(Tashkent − Samarkand) over its
  matched hours. The day, not the hour, is the unit of analysis.
- Uses all 21 days, because no model is selected from it.
- **Assumption checks, fixed in advance:**
  1. Normality of the daily differences: Shapiro–Wilk test (α = 0.05) and a Q–Q plot.
  2. Outliers: any daily difference more than 1.5 × IQR beyond the quartiles is reported.
  3. Independence between days: lag-1 autocorrelation of the daily differences is reported.
- **Primary analysis:** paired t-test on the daily differences, with a 95% confidence interval.
  If the normality check fails or outliers are present, the Wilcoxon signed-rank test is reported
  alongside it, and the bootstrap interval below is given more weight.
- **Primary bootstrap:** block bootstrap with **1-day blocks** (whole days resampled with
  replacement), 10,000 resamples, percentile 95% interval, random seed 2026.

## 5. Question 3 – next-hour temperature

- Outcome: the temperature in the **later collected reading** for the same city, one hour after
  the input reading. Forecast values from the original request are never used as the answer.
- Models:
  1. **Persistence baseline:** next-hour temperature = current temperature.
  2. **Regularised linear regression:** ridge regression, features standardised using training
     data only; penalty chosen from {0.01, 0.1, 1, 10, 100}.
  3. **Constrained random forest:** 300 trees, max depth chosen from {3, 4, 5}, minimum leaf size
     chosen from {5, 10, 20}, random seed 2026.
- Features (only values available at the input hour):
  - *Temperature-history set:* current temperature, change since the previous hour (missing at
    08:00 – filled with 0 plus a "first hour" indicator), hour of day, city (one-hot).
  - *Full set:* temperature-history set plus current humidity, wind speed and surface pressure.
- Model settings are chosen by the **lowest mean MAE across the three validation windows**.
  The full feature set is the primary set; the temperature-history set is a robustness check.
- Test-day reporting: MAE, RMSE and mean error (prediction − actual) for each model, overall, by
  city and by day; MAE improvement over persistence in %. A 5% improvement is an aspiration, not
  an expected result.
- Five test days cannot support reliable inference about model differences. The observed
  differences are reported with the day-by-day spread, and this limitation is stated. No
  significance claim is made from the test days.

## 6. Robustness checks

1. Bootstrap blocks: 1-day (primary) vs 3-day blocks, for the Question 2 interval.
2. Complete days only (8 of 8 on-the-hour batches for both cities) vs all qualifying days,
   for Question 2.
3. Temperature-history features vs the full feature set, for Question 3.

## Amendments

(Each amendment: date, what changed, why, and whether any test-day result had been seen.)

### Amendment 1 – 24 Nov 2026: implementation details for Question 3

Added before model selection was run. No model had been fitted or scored on any day, and no
test-day model result had been seen. Questions 1–2 (descriptive charts and the city comparison)
had been run as planned.

1. *Hour of day* is encoded as one indicator per input hour (08:00–14:00), not as one number, so
   that ridge regression is not forced to assume the same warming at every hour. Both models use
   the same encoding.
2. *Change since the previous hour* is set to 0 with the indicator = 1 whenever there is no reading
   exactly 60 minutes earlier for the same city. This is always the case at 08:00 and, after
   collection gaps, occasionally at other hours. The indicator is therefore named `no_previous`.
3. Model settings are chosen separately for each feature set, by the same rule (lowest mean MAE
   across the three validation windows). The chosen settings are committed in
   `results/q3_selection.json` before the test days are scored, and `models.py test` refuses to run
   until that file is committed.
