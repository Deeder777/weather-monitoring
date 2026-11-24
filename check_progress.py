"""Collection progress against the approved targets (reads weather.sqlite)."""
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else "weather.sqlite"
db = sqlite3.connect(DB)
one = lambda sql: db.execute(sql).fetchone()[0]

records = one("SELECT count(*) FROM weather_readings")
days = one("SELECT count(DISTINCT date(source_utc, '+5 hours')) FROM weather_readings")
pairs = one("""SELECT count(*) FROM weather_readings a JOIN weather_readings b
               ON b.city = a.city AND datetime(b.source_utc) = datetime(a.source_utc, '+1 hour')""")

print(f"Unique records : {records:4d}  (minimum 450, 90% target 454, maximum 504)")
print(f"Days with data : {days:4d}  (minimum 20)")
print(f"One-hour pairs : {pairs:4d}  (minimum 300, maximum 441)")
print()
print("Per Tashkent day: records | on-the-hour batches | pairs")
for day, n, onhour in db.execute("""SELECT date(source_utc, '+5 hours'), count(*),
        sum(strftime('%M', source_utc) = '00') / 3
        FROM weather_readings GROUP BY 1 ORDER BY 1"""):
    p = db.execute("""SELECT count(*) FROM weather_readings a JOIN weather_readings b
        ON b.city = a.city AND datetime(b.source_utc) = datetime(a.source_utc, '+1 hour')
        WHERE date(a.source_utc, '+5 hours') = ?""", (day,)).fetchone()[0]
    print(f"  {day}: {n:3d} | {onhour} of 8 | {p:3d}")
print()
print("Collection attempts by status:")
for status, n in db.execute("SELECT status, count(*) FROM collection_runs GROUP BY 1 ORDER BY 2 DESC"):
    print(f"  {status}: {n}")
