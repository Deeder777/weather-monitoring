"""Checkpoint 1: collect, validate, persist and retrieve city weather."""
import argparse
import hashlib
import json
import math
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent
CITIES = {"Tashkent": (41.31, 69.28), "Samarkand": (39.65, 66.96), "Bukhara": (39.77, 64.42)}
UNITS = {"temperature_2m": "°C", "relative_humidity_2m": "%", "wind_speed_10m": "km/h", "surface_pressure": "hPa"}
API = "https://api.open-meteo.com/v1/forecast"

# Assessed collection window (approved plan). Uzbekistan uses UTC+5 all year (no daylight saving),
# so a fixed offset is exact and needs no extra package on Windows.
TASHKENT = timezone(timedelta(hours=5), "Asia/Tashkent")
COLLECTION_START = date(2026, 11, 1)   # Assessed collection: 1-21 Nov 2026 (Tashkent dates).
COLLECTION_DAYS = 21
COLLECTION_HOURS = range(8, 16)   # slots 08:00 ... 15:00; a late start within the same hour still counts
SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS locations(city TEXT PRIMARY KEY, latitude REAL, longitude REAL);
CREATE TABLE IF NOT EXISTS collection_runs(id INTEGER PRIMARY KEY, city TEXT REFERENCES locations,
    collected_utc TEXT NOT NULL, source TEXT NOT NULL, response_sha256 TEXT, status TEXT NOT NULL, error TEXT);
CREATE TABLE IF NOT EXISTS weather_readings(city TEXT REFERENCES locations, source_utc TEXT NOT NULL,
    temp_c REAL NOT NULL, humidity_pct REAL NOT NULL CHECK(humidity_pct BETWEEN 0 AND 100),
    wind_kmh REAL NOT NULL CHECK(wind_kmh>=0), pressure_hpa REAL NOT NULL,
    run_id INTEGER NOT NULL REFERENCES collection_runs, PRIMARY KEY(city,source_utc));
CREATE TABLE IF NOT EXISTS raw_responses(run_id INTEGER PRIMARY KEY REFERENCES collection_runs,
    city TEXT NOT NULL REFERENCES locations, source_utc TEXT, body BLOB NOT NULL, sha256 TEXT NOT NULL);
"""

def connect(path):
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    db.executemany("INSERT OR IGNORE INTO locations VALUES(?,?,?)", [(c,*xy) for c,xy in CITIES.items()])
    db.commit()
    return db

def request_url(city):
    lat, lon = CITIES[city]
    return API + "?" + urlencode(dict(latitude=lat, longitude=lon, current=",".join(UNITS), timezone="GMT"))

def fetch(url):
    with urlopen(url, timeout=15) as response:
        return response.read()

def fixture(city):
    # Deliberately fixed: running demo twice demonstrates duplicate protection.
    values = [18 + list(CITIES).index(city), 45, 7, 974]
    return json.dumps(dict(utc_offset_seconds=0, current_units=UNITS,
        current=dict(time="2000-01-01T05:00", **dict(zip(UNITS, values))))).encode()

def parse(raw):
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("utc_offset_seconds") != 0:
        raise ValueError("Expected a UTC response")
    row, units = data.get("current"), data.get("current_units")
    if not isinstance(row, dict) or not isinstance(units, dict):
        raise ValueError("Missing current weather or units")
    stamp = datetime.strptime(row["time"], "%Y-%m-%dT%H:%M").isoformat(timespec="minutes") + "Z"
    values = []
    for name, unit in UNITS.items():
        v = row.get(name)
        if units.get(name) != unit or type(v) not in (float, int) or not math.isfinite(v):
            raise ValueError("Invalid value or unit: " + name)
        values.append(v)
    t,h,w,p = values
    if not (-100 <= t <= 70 and 0 <= h <= 100 and 0 <= w <= 500 and 300 <= p <= 1100):
        raise ValueError("Reading outside plausible range")
    return (stamp,*values)

def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def collect(db, city, demo=False, getter=fetch, pause=time.sleep):
    """Collect one city. Every response body received is kept in raw_responses.
    collected_utc is the time the response arrived (or the time the attempt failed)."""
    source = "synthetic:demo" if demo else request_url(city)
    for attempt in range(4):
        raw = digest = row = None
        try:
            raw = fixture(city) if demo else getter(source)
            stamp = now_utc()
            digest = hashlib.sha256(raw).hexdigest()
            row = parse(raw)
        except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
            stamp = now_utc()
            retry = isinstance(exc, OSError) and attempt < 3
            with db:
                run = db.execute("INSERT INTO collection_runs VALUES(NULL,?,?,?,?,?,?)",
                                 (city,stamp,source,digest,"retry" if retry else "error",str(exc))).lastrowid
                if raw is not None:
                    db.execute("INSERT INTO raw_responses VALUES(?,?,NULL,?,?)", (run,city,raw,digest))
            if retry:
                pause(2**attempt)
                continue
            return "error"
        with db:
            run = db.execute("INSERT INTO collection_runs VALUES(NULL,?,?,?,?,?,NULL)",
                             (city,stamp,source,digest,"saved")).lastrowid
            db.execute("INSERT INTO raw_responses VALUES(?,?,?,?,?)", (run,city,row[0],raw,digest))
            added = db.execute("INSERT INTO weather_readings VALUES(?,?,?,?,?,?,?) ON CONFLICT(city,source_utc) DO NOTHING",
                               (city,*row,run)).rowcount
            if added:
                return "saved"
            # Same city and source time seen before: keep the first reading, label this run.
            first = db.execute("SELECT temp_c,humidity_pct,wind_kmh,pressure_hpa FROM weather_readings WHERE city=? AND source_utc=?",
                               (city,row[0])).fetchone()
            status = "duplicate" if tuple(first) == tuple(row[1:]) else "revision"
            db.execute("UPDATE collection_runs SET status=? WHERE id=?", (status,run))
        return status

def window_problem(now):
    """Return a reason if `now` (aware datetime) is outside the approved window, else None."""
    if COLLECTION_START is None:
        return "Assessed collection has not started: COLLECTION_START is not set."
    local = now.astimezone(TASHKENT)
    end = COLLECTION_START + timedelta(days=COLLECTION_DAYS - 1)
    if not COLLECTION_START <= local.date() <= end:
        return f"Outside collection dates {COLLECTION_START} to {end} (Tashkent date {local.date()})."
    if local.hour not in COLLECTION_HOURS:
        return f"Outside collection hours 08:00-15:59 Tashkent (now {local:%H:%M})."
    return None

def collected_this_hour(db, city, now):
    """True if this city already has a saved reading from a run in the same Tashkent clock hour."""
    start = now.astimezone(TASHKENT).replace(minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    lo, hi = start.isoformat(timespec="seconds"), (start + timedelta(hours=1)).isoformat(timespec="seconds")
    return db.execute("SELECT 1 FROM collection_runs WHERE city=? AND status='saved' AND collected_utc>=? AND collected_utc<?",
                      (city, lo, hi)).fetchone() is not None

def run_live(db, now, getter=fetch, pause=time.sleep):
    """One scheduled live batch. Cities already saved this hour are skipped, so overlapping or
    repeated runs cannot add extra records; a city that failed earlier in the hour is retried."""
    results = {}
    for city in CITIES:
        if collected_this_hour(db, city, now):
            results[city] = "skipped (already collected this hour)"
        else:
            results[city] = collect(db, city, getter=getter, pause=pause)
    return results

def show(db):
    print("City | Source time (UTC) | Temp (C) | Humidity (%) | Wind (km/h) | Pressure (hPa)")
    for row in db.execute("SELECT city,source_utc,temp_c,humidity_pct,wind_kmh,pressure_hpa FROM weather_readings ORDER BY source_utc DESC,city LIMIT 12"):
        print(" | ".join(map(str,row)))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["demo","live","show-demo","show-live"])
    args = parser.parse_args()
    demo = "demo" in args.action
    if args.action == "live":
        problem = window_problem(datetime.now(timezone.utc))
        if problem:
            print("No live collection: " + problem)
            return 0
    db = connect(ROOT / ("demo.sqlite" if demo else "weather.sqlite"))
    try:
        failed = False
        if args.action == "demo":
            results = {city: collect(db,city,True) for city in CITIES}
        elif args.action == "live":
            results = run_live(db, datetime.now(timezone.utc))
        else:
            results = {}
        for city, status in results.items():
            print(city + ": " + status)
            if status == "error":
                failed = True
                print(db.execute("SELECT error FROM collection_runs WHERE city=? ORDER BY id DESC LIMIT 1",(city,)).fetchone()[0], file=sys.stderr)
        print("DEMO / synthetic readings" if demo else "Live collection / Open-Meteo")
        show(db)
        return int(failed)
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
