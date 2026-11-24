"""Question 2: do Tashkent and Samarkand differ in average daytime temperature?

Follows docs/analysis_plan.md, section 4 and robustness checks 1-2, without changes:
one paired difference per day (days with >= 6 matched hours), assumption checks fixed in
advance, paired t-test, Wilcoxon if needed, 1-day block bootstrap (10,000 resamples, seed 2026).

Run:  py -3.13 compare_cities.py
Writes the report to results/q2_city_comparison.txt and the Q-Q plot to charts/6_qq_daily_difference.png.
"""
import logging
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
DB = ROOT / "weather.sqlite"
RESAMPLES, SEED, MIN_HOURS = 10_000, 2026, 6


def daily_differences(db, complete_only=False):
    """[(day, matched_hours, mean Tashkent - Samarkand)] for qualifying days, in date order.
    complete_only: keep only days with all 8 on-the-hour readings matched (robustness check 2)."""
    rows = db.execute("""
        SELECT date(t.source_utc, '+5 hours'), strftime('%M', t.source_utc), t.temp_c - s.temp_c
        FROM weather_readings t
        JOIN weather_readings s ON s.source_utc = t.source_utc AND s.city = 'Samarkand'
        WHERE t.city = 'Tashkent'""").fetchall()
    by_day, on_hour = defaultdict(list), defaultdict(int)
    for day, minute, diff in rows:
        by_day[day].append(diff)
        on_hour[day] += minute == "00"
    out = []
    for day in sorted(by_day):
        diffs = by_day[day]
        if len(diffs) < MIN_HOURS or (complete_only and on_hour[day] < 8):
            continue
        out.append((day, len(diffs), sum(diffs) / len(diffs)))
    return out


def block_bootstrap(values, block, resamples=RESAMPLES, seed=SEED):
    """Percentile 95% interval of the mean, resampling consecutive blocks of days.
    block=1 resamples single days; block=3 uses moving blocks of three consecutive days."""
    x = np.asarray(values, dtype=float)
    n, rng = len(x), np.random.default_rng(seed)
    starts = np.arange(n - block + 1)
    per = -(-n // block)                                   # blocks needed to reach n days
    means = np.empty(resamples)
    for i in range(resamples):
        picks = rng.choice(starts, size=per)
        sample = np.concatenate([x[s:s + block] for s in picks])[:n]
        means[i] = sample.mean()
    return np.percentile(means, [2.5, 97.5])


def analyse(values):
    x = np.asarray(values, dtype=float)
    q1, q3 = np.percentile(x, [25, 75])
    iqr = q3 - q1
    outliers = [v for v in x if v < q1 - 1.5 * iqr or v > q3 + 1.5 * iqr]
    shapiro = stats.shapiro(x)
    lag1 = float(np.corrcoef(x[:-1], x[1:])[0, 1])
    t = stats.ttest_1samp(x, 0.0)
    ci = t.confidence_interval(0.95)
    wilcoxon = stats.wilcoxon(x)
    return dict(n=len(x), mean=x.mean(), sd=x.std(ddof=1), median=float(np.median(x)),
                shapiro_w=shapiro.statistic, shapiro_p=shapiro.pvalue, outliers=outliers, lag1=lag1,
                t=t.statistic, t_p=t.pvalue, t_ci=(ci.low, ci.high),
                wilcoxon_w=wilcoxon.statistic, wilcoxon_p=wilcoxon.pvalue,
                boot1=block_bootstrap(x, 1), boot3=block_bootstrap(x, 3))


def qq_plot(values, path):
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    (theory, ordered), (slope, intercept, _) = stats.probplot(values, dist="norm")
    ax.plot(theory, ordered, "o", color="#2a78d6", markersize=7)
    ax.plot(theory, slope * np.asarray(theory) + intercept, color="#898781", lw=1.5)
    ax.set_xlabel("Theoretical normal quantiles")
    ax.set_ylabel("Daily difference (°C)")
    ax.set_title("6. Q–Q plot: Tashkent − Samarkand daily differences", loc="left", fontweight="bold", fontsize=11)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    path.parent.mkdir(exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fmt_p(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def report(days, r, label):
    lines = [f"== {label}: {r['n']} days ({days[0][0]} to {days[-1][0]}) ==",
             f"Mean difference (Tashkent - Samarkand): {r['mean']:+.2f} °C   SD {r['sd']:.2f}   median {r['median']:+.2f}",
             "Assumption checks (fixed in advance):",
             f"  1. Shapiro-Wilk: W = {r['shapiro_w']:.3f}, {fmt_p(r['shapiro_p'])}"
             + ("  -> normality not rejected at 0.05" if r['shapiro_p'] >= 0.05 else "  -> normality rejected at 0.05"),
             f"  2. Outliers (1.5 x IQR): {len(r['outliers'])}"
             + (f"  {[round(v, 2) for v in r['outliers']]}" if r['outliers'] else ""),
             f"  3. Lag-1 autocorrelation of daily differences: {r['lag1']:+.2f}",
             f"Paired t-test: t({r['n'] - 1}) = {r['t']:.2f}, {fmt_p(r['t_p'])}, "
             f"95% CI [{r['t_ci'][0]:+.2f}, {r['t_ci'][1]:+.2f}] °C",
             f"Wilcoxon signed-rank: W = {r['wilcoxon_w']:.1f}, {fmt_p(r['wilcoxon_p'])}"
             + ("   (reported because a check failed)" if r['shapiro_p'] < 0.05 or r['outliers'] else "   (reported for reference)"),
             f"Block bootstrap, 1-day blocks (primary): 95% CI [{r['boot1'][0]:+.2f}, {r['boot1'][1]:+.2f}] °C",
             f"Block bootstrap, 3-day blocks (robustness 1): 95% CI [{r['boot3'][0]:+.2f}, {r['boot3'][1]:+.2f}] °C"]
    return lines


def main():
    if not DB.exists():
        print("weather.sqlite not found. Get it first:\n"
              "  git fetch origin data\n  git restore --source=origin/data -- weather.sqlite")
        return 1
    db = sqlite3.connect(DB)
    try:
        all_days = daily_differences(db)
        complete = daily_differences(db, complete_only=True)
    finally:
        db.close()
    lines = ["Question 2: Tashkent vs Samarkand daytime temperature (exploratory; days are the unit)",
             f"Settings: >= {MIN_HOURS} matched hours per day, {RESAMPLES} resamples, seed {SEED}", ""]
    lines += ["Daily differences:"] + [f"  {d}  {h} h  {v:+.2f} °C" for d, h, v in all_days] + [""]
    lines += report(all_days, analyse([v for _, _, v in all_days]), "All qualifying days (primary)") + [""]
    lines += report(complete, analyse([v for _, _, v in complete]), "Complete days only (robustness 2)")
    text = "\n".join(lines)
    out = ROOT / "results" / "q2_city_comparison.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    qq_plot([v for _, _, v in all_days], ROOT / "charts" / "6_qq_daily_difference.png")
    print(text)
    print("\nsaved results/q2_city_comparison.txt and charts/6_qq_daily_difference.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
