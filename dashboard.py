"""Local Streamlit dashboard for the weather project.

Run:  py -3.13 -m streamlit run dashboard.py
Reads weather.sqlite (the live database from the data branch). If it is missing, it uses the bundled
offline snapshot data/weather_snapshot.sqlite. The optional live check fetches current conditions
from Open-Meteo for display only: it never writes to any database.
"""
import json
from contextlib import closing
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import models
import queries
import weather

ROOT = Path(__file__).resolve().parent
LIVE_DB, SNAPSHOT_DB = ROOT / "weather.sqlite", ROOT / "data" / "weather_snapshot.sqlite"
CITIES = ["Tashkent", "Samarkand", "Bukhara"]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]          # same colour per city as in charts.py
CITY_SCALE = alt.Scale(domain=CITIES, range=COLORS)
VARIABLES = {"temp_c": "Temperature (°C)", "humidity_pct": "Relative humidity (%)",
             "wind_kmh": "Wind speed (km/h)", "pressure_hpa": "Surface pressure (hPa)"}
TASHKENT = timezone(timedelta(hours=5))

st.set_page_config(page_title="Weather monitoring – Tashkent, Samarkand, Bukhara", layout="wide")


def database_path():
    return LIVE_DB if LIVE_DB.exists() else SNAPSHOT_DB if SNAPSHOT_DB.exists() else None


@st.cache_data
def load_readings(path):
    with closing(sqlite3.connect(path)) as db:
        df = pd.read_sql_query("SELECT city, source_utc, temp_c, humidity_pct, wind_kmh, pressure_hpa "
                               "FROM weather_readings", db)
    df["time"] = pd.to_datetime(df["source_utc"].str.rstrip("Z")) + pd.Timedelta(hours=5)
    df["day"] = df["time"].dt.date
    return df.sort_values(["time", "city"])


@st.cache_data
def run_query(path, number):
    with closing(sqlite3.connect(path)) as db:
        names, rows = queries.run(db, number)
    return pd.DataFrame(rows, columns=names)


@st.cache_resource
def deployment_model(path):
    """Ridge regression with the committed setting, refitted on ALL collected pairs.
    Used only for the next-hour estimate; the reported evaluation is the one-time test in results/."""
    selection = json.loads(models.SELECTION.read_text(encoding="utf-8"))
    setting = selection["chosen"]["full"]["ridge"]["setting"]
    with closing(sqlite3.connect(path)) as db:
        pairs = models.load_pairs(db)
    model = models.make_model("ridge", setting)
    model.fit(models.features(pairs, "full"), models.target(pairs))
    return model, setting, len(pairs)


def previous_temp(df, city, time):
    match = df[(df["city"] == city) & (df["time"] == time - pd.Timedelta(hours=1))]
    return None if match.empty else float(match["temp_c"].iloc[0])


def estimate(model, reading, before):
    """Next-hour estimate for one reading (dict with city, hour, temp_c, humidity_pct, wind_kmh, pressure_hpa)."""
    row = dict(city=reading["city"], hour=reading["hour"], temp=reading["temp_c"], hum=reading["humidity_pct"],
               wind=reading["wind_kmh"], pres=reading["pressure_hpa"],
               change=reading["temp_c"] - before if before is not None else 0.0,
               no_previous=0 if before is not None else 1)
    return float(model.predict(models.features([row], "full"))[0])


def city_line(df, y, title, x="time", per_day=False):
    """Line per city. per_day=True draws a separate segment for each day, so no line crosses the night
    (nothing was measured between 15:00 and 08:00)."""
    extra = {"detail": "day_label:N"} if per_day else {}
    if per_day:
        df = df.assign(day_label=df["day"].astype(str)).drop(columns="day")
    return (alt.Chart(df).mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=30))
            .encode(x=alt.X(x, title=None), y=alt.Y(y, title=title, scale=alt.Scale(zero=False)), **extra,
                    color=alt.Color("city:N", scale=CITY_SCALE, legend=alt.Legend(title=None, orient="top")),
                    tooltip=["city", alt.Tooltip(x), alt.Tooltip(y, format=".1f")])
            .properties(height=320))


path = database_path()
st.title("Live weather monitoring")
st.caption("Tashkent, Samarkand and Bukhara · 08:00–15:00 Tashkent time · 1–21 Nov 2026 · "
           "Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0). "
           "Values are model-derived estimates, not station measurements.")
if path is None:
    st.error("No database found. Run `git fetch origin data` and "
             "`git restore --source=origin/data -- weather.sqlite`, or add the offline snapshot.")
    st.stop()
st.caption(f"Data source: `{path.relative_to(ROOT)}`" + (" (offline snapshot)" if path == SNAPSHOT_DB else ""))

df = load_readings(str(path))
overview, compare, history, quality, nexthour = st.tabs(
    ["Overview", "City comparison", "History", "Collection quality", "Next-hour estimate"])

with overview:
    pairs = run_query(str(path), 5)["pairs"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Unique records", len(df), help="Minimum 450; maximum 504")
    c2.metric("Days with data", df["day"].nunique(), help="Minimum 20")
    c3.metric("One-hour pairs", int(pairs), help="Minimum 300; maximum 441")
    st.subheader("Latest reading per city")
    st.dataframe(run_query(str(path), 1), hide_index=True, width="stretch")
    st.info("Records are repeated hourly readings of three cities, not independent observations. "
            "All results are exploratory and apply only to these cities, dates and daytime hours.")

with compare:
    st.subheader("Matched daytime summary")
    st.caption("Only hours where all three cities have a reading.")
    st.dataframe(run_query(str(path), 2), hide_index=True, width="stretch")
    counts = df.groupby("time")["city"].transform("count")
    matched = df[(counts == 3) & (df["time"].dt.minute == 0)].copy()
    matched["hour"] = matched["time"].dt.strftime("%H:00")
    profile = matched.groupby(["city", "hour"], as_index=False)["temp_c"].mean()
    st.subheader("Average temperature by hour")
    st.altair_chart(city_line(profile, "temp_c", "Mean temperature (°C)", x="hour:O"), width="stretch")
    st.subheader("Tashkent − Samarkand, one difference per day")
    diff = run_query(str(path), 4)
    diff["warmer"] = diff["mean_difference_c"].map(lambda v: "Tashkent warmer" if v >= 0 else "Samarkand warmer")
    st.altair_chart(alt.Chart(diff).mark_bar(cornerRadius=2).encode(
        x=alt.X("tashkent_day:O", title=None), y=alt.Y("mean_difference_c:Q", title="°C"),
        color=alt.Color("warmer:N", scale=alt.Scale(domain=["Tashkent warmer", "Samarkand warmer"],
                                                    range=["#2a78d6", "#e34948"]), legend=alt.Legend(title=None, orient="top")),
        tooltip=["tashkent_day", "matched_hours", "mean_difference_c"]).properties(height=280),
        width="stretch")
    report = ROOT / "results" / "q2_city_comparison.txt"
    if report.exists():
        with st.expander("Statistical result (Question 2, as pre-registered)"):
            st.code(report.read_text(encoding="utf-8"), language=None)

with history:
    left, right = st.columns([1, 3])
    with left:
        chosen = st.multiselect("Cities", CITIES, default=CITIES)
        variable = st.selectbox("Variable", list(VARIABLES), format_func=VARIABLES.get)
        first, last = df["day"].min(), df["day"].max()
        start, end = st.slider("Dates", min_value=first, max_value=last, value=(first, last), format="DD MMM")
    view = df[df["city"].isin(chosen) & (df["day"] >= start) & (df["day"] <= end)]
    with right:
        if view.empty:
            st.warning("No readings for this selection.")
        else:
            st.altair_chart(city_line(view, variable, VARIABLES[variable], per_day=True).properties(height=380),
                            width="stretch")
    st.dataframe(view[["city", "time", "temp_c", "humidity_pct", "wind_kmh", "pressure_hpa"]],
                 hide_index=True, width="stretch", height=260)

with quality:
    q3 = run_query(str(path), 3)
    st.subheader("Saved readings and logged attempts per day")
    st.altair_chart(alt.Chart(q3).mark_bar(cornerRadius=2, color="#2a78d6").encode(
        x=alt.X("tashkent_day:O", title=None), y=alt.Y("saved:Q", title="Saved readings"),
        tooltip=list(q3.columns)).properties(height=300), width="stretch")
    q3["failed"] = q3["retry"] + q3["error"]
    st.altair_chart(alt.Chart(q3).mark_bar(cornerRadius=2, color="#d03b3b").encode(
        x=alt.X("tashkent_day:O", title=None), y=alt.Y("failed:Q", title="Failed attempts"),
        tooltip=["tashkent_day", "retry", "error"]).properties(height=280), width="stretch")
    st.caption("Failed attempts = retries + errors (mostly Open-Meteo connection timeouts).")
    st.dataframe(q3.drop(columns="failed"), hide_index=True, width="stretch")
    expected = {(c, datetime(2026, 11, 1 + d, h)) for c in CITIES for d in range(21) for h in range(8, 16)}
    have = {(r.city, r.time.to_pydatetime()) for r in df.itertuples()}
    missing = sorted(expected - have, key=lambda x: (x[1], CITIES.index(x[0])))
    st.subheader(f"Missing on-the-hour slots: {len(missing)}")
    st.dataframe(pd.DataFrame([(t.strftime("%Y-%m-%d %H:%M"), c) for c, t in missing],
                              columns=["Tashkent time", "city"]), hide_index=True, width="stretch")
    st.caption("Missed hours are never filled from a historical download or invented.")

with nexthour:
    test_report = ROOT / "results" / "q3_test.txt"
    if not models.SELECTION.exists():
        st.warning("No committed model settings yet (results/q3_selection.json). Run `py -3.13 models.py select`.")
    else:
        model, setting, n_pairs = deployment_model(str(path))
        st.subheader("Estimate from a stored reading")
        st.caption(f"Ridge regression (alpha = {setting['alpha']}), refitted on all {n_pairs} collected pairs. "
                   "The reported accuracy comes from the one-time test on 17–21 Nov below, not from this refit, "
                   "so the 'actual' values shown here are a demonstration, not an evaluation.")
        times = sorted({t for t in df["time"] if t.minute == 0 and t.hour in models.INPUT_HOURS}, reverse=True)
        when = st.selectbox("Input reading (Tashkent time)", times, format_func=lambda t: f"{t:%d %b %Y, %H:%M}")
        cols = st.columns(3)
        for col, city in zip(cols, CITIES):
            row = df[(df["city"] == city) & (df["time"] == when)]
            if row.empty:
                col.metric(city, "no reading", help="This city has no stored reading at this time")
                continue
            r = row.iloc[0]
            value = estimate(model, dict(city=city, hour=int(when.hour), **r[list(VARIABLES)].to_dict()),
                             previous_temp(df, city, when))
            actual = df[(df["city"] == city) & (df["time"] == when + pd.Timedelta(hours=1))]
            col.metric(f"{city} at {when + pd.Timedelta(hours=1):%H:%M}", f"{value:.1f} °C",
                       delta=f"{value - r['temp_c']:+.1f} °C vs {when:%H:%M}", delta_color="off")
            col.caption(f"Now {r['temp_c']:.1f} °C · persistence {r['temp_c']:.1f} °C · "
                        + (f"actual {actual['temp_c'].iloc[0]:.1f} °C" if not actual.empty else "no later reading"))
        st.subheader("Collect a new record now (needs internet)")
        st.caption("Runs the same collector, validation and storage code as the assessed collection, but saves to "
                   "`post_collection.sqlite`. These records are never part of the assessed 1–21 Nov dataset or results.")
        if st.button("Collect, save and estimate"):
            with weather.connect(weather.CHECK_DB) as cdb:
                statuses = weather.check_batch(cdb)
                rows = pd.read_sql_query(
                    "SELECT w.city, w.source_utc, w.temp_c, w.humidity_pct, w.wind_kmh, w.pressure_hpa, r.collected_utc "
                    "FROM weather_readings w JOIN collection_runs r ON r.id = w.run_id "
                    "WHERE w.source_utc = (SELECT max(source_utc) FROM weather_readings WHERE city = w.city)", cdb)
            cdb.close()
            for city, status in statuses.items():
                if status == "error":
                    st.error(f"{city}: collection failed (logged in collection_runs). Check the internet connection.")
                    continue
                row = rows[rows["city"] == city]
                if row.empty:
                    continue
                r = row.iloc[0]
                local = datetime.strptime(r["source_utc"], "%Y-%m-%dT%H:%MZ") + timedelta(hours=5)
                line = (f"**{city}** ({status}): {r['temp_c']:.1f} °C at {local:%d %b %H:%M} Tashkent, "
                        f"retrieved {r['collected_utc']}")
                if local.hour in models.INPUT_HOURS:
                    value = estimate(model, dict(city=city, hour=local.hour, temp_c=r["temp_c"],
                                                 humidity_pct=r["humidity_pct"], wind_kmh=r["wind_kmh"],
                                                 pressure_hpa=r["pressure_hpa"]), None)
                    line += f" → estimate **{value:.1f} °C** at {local + timedelta(hours=1):%H:%M}"
                else:
                    line += " (outside the 08:00–14:00 model window, so no estimate)"
                st.write(line)
            st.caption("Saved → retrieved from the database → estimate. 'duplicate' means Open-Meteo has not published "
                       "a newer 15-minute value since the last collection.")
        if test_report.exists():
            with st.expander("Model evaluation (Question 3, one-time test on 17–21 Nov)", expanded=True):
                st.code(test_report.read_text(encoding="utf-8"), language=None)
