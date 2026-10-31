"""Checkpoint 1: collect, validate, persist and retrieve city weather."""
import argparse
import hashlib
import json
import math
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent
CITIES = {"Tashkent": (41.31, 69.28), "Samarkand": (39.65, 66.96), "Bukhara": (39.77, 64.42)}
UNITS = {"temperature_2m": "°C", "relative_humidity_2m": "%", "wind_speed_10m": "km/h", "surface_pressure": "hPa"}
API = "https://api.open-meteo.com/v1/forecast"
SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS locations(city TEXT PRIMARY KEY, latitude REAL, longitude REAL);
CREATE TABLE IF NOT EXISTS collection_runs(id INTEGER PRIMARY KEY, city TEXT REFERENCES locations,
    collected_utc TEXT NOT NULL, source TEXT NOT NULL, response_sha256 TEXT, status TEXT NOT NULL, error TEXT);
CREATE TABLE IF NOT EXISTS weather_readings(city TEXT REFERENCES locations, source_utc TEXT NOT NULL,
    temp_c REAL NOT NULL, humidity_pct REAL NOT NULL CHECK(humidity_pct BETWEEN 0 AND 100),
    wind_kmh REAL NOT NULL CHECK(wind_kmh>=0), pressure_hpa REAL NOT NULL,
    run_id INTEGER NOT NULL REFERENCES collection_runs, PRIMARY KEY(city,source_utc));
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

def collect(db, city, demo=False, getter=fetch, pause=time.sleep):
    source = "synthetic:demo" if demo else request_url(city)
    for attempt in range(4):
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        digest = None
        try:
            raw = fixture(city) if demo else getter(source)
            digest = hashlib.sha256(raw).hexdigest()
            row = parse(raw)
        except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
            retry = isinstance(exc, OSError) and attempt < 3
            with db:
                db.execute("INSERT INTO collection_runs VALUES(NULL,?,?,?,?,?,?)",
                           (city,stamp,source,digest,"retry" if retry else "error",str(exc)))
            if retry:
                pause(2**attempt)
                continue
            return "error"
        with db:
            run = db.execute("INSERT INTO collection_runs VALUES(NULL,?,?,?,?,?,NULL)",
                             (city,stamp,source,digest,"saved")).lastrowid
            added = db.execute("INSERT INTO weather_readings VALUES(?,?,?,?,?,?,?) ON CONFLICT(city,source_utc) DO NOTHING",
                               (city,*row,run)).rowcount
            if not added:
                db.execute("UPDATE collection_runs SET status='duplicate' WHERE id=?", (run,))
        return "saved" if added else "duplicate"

def show(db):
    print("City | Source time (UTC) | Temp (C) | Humidity (%) | Wind (km/h) | Pressure (hPa)")
    for row in db.execute("SELECT city,source_utc,temp_c,humidity_pct,wind_kmh,pressure_hpa FROM weather_readings ORDER BY source_utc DESC,city LIMIT 12"):
        print(" | ".join(map(str,row)))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["demo","live","show-demo","show-live"])
    args = parser.parse_args()
    demo = "demo" in args.action
    db = connect(ROOT / ("demo.sqlite" if demo else "weather.sqlite"))
    try:
        failed = False
        if args.action in ("demo","live"):
            for city in CITIES:
                status = collect(db,city,demo)
                print(city + ": " + status)
                failed |= status == "error"
                if status == "error":
                    print(db.execute("SELECT error FROM collection_runs WHERE city=? ORDER BY id DESC LIMIT 1",(city,)).fetchone()[0], file=sys.stderr)
        print("DEMO / synthetic readings" if demo else "Live collection / Open-Meteo")
        show(db)
        return int(failed)
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
