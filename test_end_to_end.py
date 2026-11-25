"""Integration tests: a new record goes through collection -> database -> query -> model input."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import models
import queries
import weather as w


def response(stamp, temp):
    """A valid Open-Meteo-style response (synthetic test fixture, never used in analysis)."""
    current = dict(time=stamp, temperature_2m=temp, relative_humidity_2m=50, wind_speed_10m=5.0, surface_pressure=970.0)
    return json.dumps(dict(utc_offset_seconds=0, current_units=w.UNITS, current=current)).encode()


class EndToEndTests(unittest.TestCase):
    def test_new_record_is_saved_retrieved_and_becomes_model_input(self):
        db = w.connect(":memory:")
        self.addCleanup(db.close)
        first = w.check_batch(db, getter=lambda url: response("2030-01-02T05:00", 12.0))   # 10:00 Tashkent
        second = w.check_batch(db, getter=lambda url: response("2030-01-02T06:00", 13.5))  # 11:00 Tashkent
        self.assertEqual(set(first.values()) | set(second.values()), {"saved"})
        names, rows = queries.run(db, 1)                                  # query 1: latest reading per city
        latest = {r[0]: r for r in rows}
        self.assertEqual(latest["Tashkent"][names.index("temp_c")], 13.5)
        provenance = db.execute("SELECT source, collected_utc FROM collection_runs WHERE status='saved'").fetchall()
        self.assertTrue(all(src.startswith(w.API) and stamp for src, stamp in provenance))
        pairs = models.load_pairs(db)                                     # 10:00 -> 11:00 is a valid pair
        self.assertEqual(len(pairs), 3)
        self.assertEqual({(p["hour"], p["temp"], p["target"]) for p in pairs}, {(10, 12.0, 13.5)})
        self.assertEqual(models.features(pairs, "full").shape[0], 3)

    def test_check_mode_writes_only_to_the_separate_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            check_db = Path(tmp) / "post_collection.sqlite"
            fake = lambda url: response("2030-01-02T05:00", 12.0)
            with mock.patch.object(w, "CHECK_DB", check_db), mock.patch.object(w, "ROOT", Path(tmp)), \
                 mock.patch.object(w, "fetch", fake), mock.patch("sys.argv", ["weather.py", "check"]):
                self.assertEqual(w.main(), 0)          # works any day: no collection-window refusal
            db = sqlite3.connect(check_db)            # closed before the folder is removed (Windows)
            try:
                self.assertEqual(db.execute("SELECT count(*) FROM weather_readings").fetchone()[0], 3)
            finally:
                db.close()
            self.assertFalse((Path(tmp) / "weather.sqlite").exists())    # assessed database untouched


if __name__ == "__main__":
    unittest.main()
