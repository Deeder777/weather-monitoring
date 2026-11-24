"""The five planned visualisations, saved as PNG files in the charts/ folder.

Run:  py -3.13 charts.py
Needs matplotlib (py -3.13 -m pip install -r requirements.txt) and weather.sqlite in this folder.
Charts 1-4 describe the data (Questions 1 and 2 in docs/analysis_plan.md, all 21 days).
Chart 5 shows collection quality. No chart shows model results or uses test days for modelling.
"""
import logging
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)   # quiet font fallback
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker

ROOT = Path(__file__).resolve().parent
DB, OUT = ROOT / "weather.sqlite", ROOT / "charts"
CITIES = ["Tashkent", "Samarkand", "Bukhara"]
COLOR = {"Tashkent": "#2a78d6", "Samarkand": "#eb6834", "Bukhara": "#1baf7a"}   # fixed per city
INK, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
WARM, COOL, CRITICAL = "#e34948", "#2a78d6", "#d03b3b"
TEST_START = datetime(2026, 11, 17)

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"], "font.size": 10,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": "#52514e", "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "legend.frameon": False, "lines.linewidth": 2,
})


def load(db):
    """Readings as dicts with Tashkent local time."""
    rows = db.execute("SELECT city, source_utc, temp_c, humidity_pct, wind_kmh FROM weather_readings")
    out = []
    for city, stamp, t, h, w in rows:
        local = datetime.strptime(stamp, "%Y-%m-%dT%H:%MZ") + timedelta(hours=5)
        out.append(dict(city=city, time=local, temp=t, hum=h, wind=w))
    return sorted(out, key=lambda r: r["time"])


def label_ends(ax, ends, gap):
    """Direct-label line ends, nudging labels apart so they never overlap. ends: [(x, y, text)]."""
    placed = []
    for x, y, text in sorted(ends, key=lambda e: e[1]):
        if placed and y - placed[-1] < gap:
            y = placed[-1] + gap
        placed.append(y)
        ax.annotate(text, (x, y), xytext=(8, 0), textcoords="offset points", va="center", color=INK, fontsize=9)


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("saved charts/" + name)


def chart_timeseries(data):
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.axvspan(TEST_START, TEST_START + timedelta(days=5), color="#f0efec", zorder=0, lw=0)
    ax.text(TEST_START + timedelta(hours=6), 0.97, "Final 5 days: held out for model testing",
            transform=ax.get_xaxis_transform(), va="top", color=MUTED, fontsize=9)
    ends = []
    for city in CITIES:
        xs, ys, last_day = [], [], None
        for r in (r for r in data if r["city"] == city):
            if last_day and r["time"].date() != last_day:      # break the line overnight
                xs.append(r["time"] - timedelta(hours=12)); ys.append(float("nan"))
            xs.append(r["time"]); ys.append(r["temp"]); last_day = r["time"].date()
        ax.plot(xs, ys, color=COLOR[city], label=city)
        ends.append((xs[-1], ys[-1], city))
    span = max(r["temp"] for r in data) - min(r["temp"] for r in data)
    label_ends(ax, ends, gap=span * 0.06)
    ax.set_xlim(datetime(2026, 11, 1), datetime(2026, 11, 23, 12))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_ylabel("Temperature (°C)")
    ax.set_title("1. Daytime temperature, 08:00–15:00 Tashkent, 1–21 Nov 2026")
    ax.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, -0.1))
    save(fig, "1_temperature_timeseries.png")


def matched(data):
    """Only readings at source times where all three cities have a value."""
    count = defaultdict(int)
    for r in data:
        count[r["time"]] += 1
    return [r for r in data if count[r["time"]] == 3]


def chart_hourly_profile(data):
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    rows = [r for r in matched(data) if r["time"].minute == 0]
    ends = []
    for city in CITIES:
        hours = range(8, 16)
        means = []
        for h in hours:
            v = [r["temp"] for r in rows if r["city"] == city and r["time"].hour == h]
            means.append(sum(v) / len(v) if v else float("nan"))
        ax.plot(list(hours), means, color=COLOR[city], marker="o", markersize=6, label=city)
        ends.append((15, means[-1], city))
    label_ends(ax, ends, gap=(ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.05)
    ax.set_xticks(range(8, 16), [f"{h:02d}:00" for h in range(8, 16)])
    ax.set_xlim(7.7, 15.9)
    ax.set_ylabel("Mean temperature (°C)")
    ax.set_xlabel("Hour (Tashkent time)")
    ax.set_title("2. Average temperature by hour (matched hours only)")
    ax.legend(loc="upper left")
    save(fig, "2_hourly_profile.png")


def chart_humidity_wind(data):
    rows = matched(data)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, key, label in [(axes[0], "hum", "Relative humidity (%)"), (axes[1], "wind", "Wind speed (km/h)")]:
        values = [[r[key] for r in rows if r["city"] == c] for c in CITIES]
        box = ax.boxplot(values, patch_artist=True, widths=0.5, medianprops=dict(color=INK, lw=1.5),
                         whiskerprops=dict(color=MUTED), capprops=dict(color=MUTED),
                         flierprops=dict(marker="o", markersize=3, markerfacecolor=MUTED, markeredgecolor="none"))
        for patch, city in zip(box["boxes"], CITIES):
            patch.set(facecolor=COLOR[city], alpha=0.85, edgecolor=SURFACE)
        ax.set_xticks([1, 2, 3], CITIES)
        ax.set_ylabel(label)
        ax.grid(axis="x", visible=False)
    axes[0].set_title("3. Humidity and wind by city (matched hours)")
    save(fig, "3_humidity_wind_by_city.png")


def chart_daily_difference(data):
    by_time = defaultdict(dict)
    for r in data:
        by_time[r["time"]][r["city"]] = r["temp"]
    per_day = defaultdict(list)
    for t, v in by_time.items():
        if "Tashkent" in v and "Samarkand" in v:
            per_day[t.date()].append(v["Tashkent"] - v["Samarkand"])
    days = sorted(d for d, diffs in per_day.items() if len(diffs) >= 6)
    diffs = [sum(per_day[d]) / len(per_day[d]) for d in days]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.bar(days, diffs, width=0.7, color=[COOL if d >= 0 else WARM for d in diffs], edgecolor=SURFACE, linewidth=1)
    ax.axhline(0, color=AXIS, lw=1)
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_ylabel("Tashkent − Samarkand (°C)")
    ax.set_title(f"4. Daily mean temperature difference ({len(days)} days with ≥ 6 matched hours)")
    ax.text(0.01, 0.97, "Above 0: Tashkent warmer", transform=ax.transAxes, va="top", color=COOL, fontsize=9)
    ax.text(0.01, 0.03, "Below 0: Samarkand warmer", transform=ax.transAxes, va="bottom", color=WARM, fontsize=9)
    ax.grid(axis="x", visible=False)
    save(fig, "4_daily_difference.png")


def chart_quality(db):
    days = [datetime(2026, 11, 1) + timedelta(days=i) for i in range(21)]
    saved = dict(db.execute("SELECT date(source_utc, '+5 hours'), sum(strftime('%M', source_utc) = '00') "
                            "FROM weather_readings GROUP BY 1").fetchall())
    failed = dict(db.execute("SELECT date(collected_utc, '+5 hours'), sum(status IN ('retry', 'error')) "
                             "FROM collection_runs GROUP BY 1").fetchall())
    keys = [d.strftime("%Y-%m-%d") for d in days]
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 5.2), sharex=True, gridspec_kw=dict(height_ratios=[3, 2]))
    top.bar(days, [saved.get(k, 0) for k in keys], width=0.7, color=COLOR["Tashkent"], edgecolor=SURFACE, linewidth=1)
    top.axhline(24, color=MUTED, lw=1, ls="--")
    top.text(days[0], 24.6, "24 possible per day", va="bottom", color=MUTED, fontsize=9)
    top.set_ylabel("On-the-hour readings")
    top.set_ylim(0, 27)
    top.set_title("5. Collection quality per day")
    bottom.bar(days, [failed.get(k, 0) for k in keys], width=0.7, color=CRITICAL, edgecolor=SURFACE, linewidth=1)
    bottom.set_ylabel("Failed attempts\n(retry + error)")
    bottom.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    bottom.set_xlim(days[0] - timedelta(hours=18), days[-1] + timedelta(hours=18))
    bottom.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    bottom.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    for ax in (top, bottom):
        ax.grid(axis="x", visible=False)
    save(fig, "5_collection_quality.png")


def main():
    if not DB.exists():
        print("weather.sqlite not found. Get it first:\n"
              "  git fetch origin data\n  git restore --source=origin/data -- weather.sqlite")
        return 1
    db = sqlite3.connect(DB)
    try:
        data = load(db)
        chart_timeseries(data)
        chart_hourly_profile(data)
        chart_humidity_wind(data)
        chart_daily_difference(data)
        chart_quality(db)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
