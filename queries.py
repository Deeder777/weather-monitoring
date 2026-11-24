"""The five planned database queries (UDE5014CM weather project).

Run:  py -3.13 queries.py          (all five)
      py -3.13 queries.py 3        (one query)
Reads weather.sqlite in this folder. Times are shown in Asia/Tashkent (UTC+5).
Query 5 only counts prediction pairs; it never shows test-day values (see docs/analysis_plan.md).
"""
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent / "weather.sqlite"
TEST_FIRST_DAY = "2026-11-17"          # final five days are held out for model evaluation
LOCAL = "datetime(source_utc, '+5 hours')"

QUERIES = {
    1: ("Latest reading for each city", f"""
        SELECT city, {LOCAL} AS tashkent_time, temp_c, humidity_pct, wind_kmh, pressure_hpa
        FROM weather_readings w
        WHERE source_utc = (SELECT max(source_utc) FROM weather_readings WHERE city = w.city)
        ORDER BY city"""),

    2: ("Matched daytime summary (only hours where all three cities have a reading)", f"""
        WITH matched AS (
            SELECT source_utc FROM weather_readings GROUP BY source_utc HAVING count(*) = 3)
        SELECT city, count(*) AS readings,
               round(avg(temp_c), 2) AS mean_temp, min(temp_c) AS min_temp, max(temp_c) AS max_temp,
               round(avg(humidity_pct), 1) AS mean_humidity, round(avg(wind_kmh), 1) AS mean_wind
        FROM weather_readings JOIN matched USING (source_utc)
        GROUP BY city ORDER BY city"""),

    3: ("Collection quality per day: saved readings and logged attempts", f"""
        SELECT date(collected_utc, '+5 hours') AS tashkent_day,
               sum(status = 'saved') AS saved, sum(status = 'duplicate') AS duplicate,
               sum(status = 'revision') AS revision, sum(status = 'retry') AS retry,
               sum(status = 'error') AS error,
               (SELECT count(*) FROM weather_readings
                WHERE date({LOCAL}) = date(r.collected_utc, '+5 hours')
                  AND strftime('%M', source_utc) <> '00') AS off_the_hour
        FROM collection_runs r
        GROUP BY tashkent_day ORDER BY tashkent_day"""),

    4: ("Tashkent minus Samarkand: one paired difference per day (days with >= 6 matched hours)", f"""
        SELECT date(t.source_utc, '+5 hours') AS tashkent_day,
               count(*) AS matched_hours,
               round(avg(t.temp_c - s.temp_c), 2) AS mean_difference_c
        FROM weather_readings t
        JOIN weather_readings s ON s.source_utc = t.source_utc AND s.city = 'Samarkand'
        WHERE t.city = 'Tashkent'
        GROUP BY tashkent_day HAVING count(*) >= 6
        ORDER BY tashkent_day"""),

    5: ("Valid one-hour prediction pairs (same city, source times exactly 60 minutes apart)", f"""
        SELECT a.city,
               CASE WHEN date(a.source_utc, '+5 hours') < '{TEST_FIRST_DAY}'
                    THEN 'development' ELSE 'test' END AS split,
               count(*) AS pairs
        FROM weather_readings a
        JOIN weather_readings b
          ON b.city = a.city AND datetime(b.source_utc) = datetime(a.source_utc, '+1 hour')
        GROUP BY a.city, split ORDER BY split, a.city"""),
}


def run(db, number):
    """Return (column names, rows) for one query."""
    cursor = db.execute(QUERIES[number][1])
    return [c[0] for c in cursor.description], cursor.fetchall()


def main(argv):
    if not DB.exists():
        print("weather.sqlite not found. Get it first:\n"
              "  git fetch origin data\n  git restore --source=origin/data -- weather.sqlite")
        return 1
    numbers = [int(a) for a in argv] or sorted(QUERIES)
    db = sqlite3.connect(DB)
    try:
        for n in numbers:
            names, rows = run(db, n)
            print(f"\nQuery {n}: {QUERIES[n][0]}")
            print(" | ".join(names))
            for row in rows:
                print(" | ".join(str(v) for v in row))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
