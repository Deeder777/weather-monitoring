"""List every expected slot (21 days x 8 hours x 3 cities) that is missing or not on the hour."""
import sqlite3
import sys
from datetime import date, timedelta

DB = sys.argv[1] if len(sys.argv) > 1 else "weather.sqlite"
START, DAYS, HOURS = date(2026, 11, 1), 21, range(8, 16)
CITIES = ["Tashkent", "Samarkand", "Bukhara"]

db = sqlite3.connect(DB)
rows = db.execute("SELECT city, datetime(source_utc, '+5 hours') FROM weather_readings").fetchall()
have = {(c, t[:16]) for c, t in rows}          # Tashkent local 'YYYY-MM-DD HH:MM'

print("Missing on-the-hour slots (Tashkent time):")
missing = 0
for d in range(DAYS):
    day = START + timedelta(days=d)
    for h in HOURS:
        slot = f"{day} {h:02d}:00"
        absent = [c for c in CITIES if (c, slot) not in have]
        if absent:
            missing += len(absent)
            print(f"  {slot}  {', '.join(absent)}")
print(f"  total: {missing} city-slots\n")

print("Records not on the hour (Tashkent time):")
off = sorted((t, c) for c, t in have if not t.endswith(":00"))
for t, c in off:
    print(f"  {t}  {c}")
print(f"  total: {len(off)}")
