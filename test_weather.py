import json
import unittest
from datetime import date, datetime, timezone
from urllib.error import URLError
import weather as w

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.db = w.connect(":memory:")
        self.addCleanup(self.db.close)

    def test_persist_and_deduplicate(self):
        for city in w.CITIES:
            self.assertEqual(w.collect(self.db,city,True),"saved")
            self.assertEqual(w.collect(self.db,city,True),"duplicate")
        self.assertEqual(self.db.execute("SELECT count(*) FROM weather_readings").fetchone()[0],3)
        self.assertEqual(self.db.execute("SELECT count(*) FROM collection_runs").fetchone()[0],6)

    def test_bad_response_does_not_become_weather(self):
        for key,bad in [("relative_humidity_2m",150),("wind_speed_10m",-1),("time","invalid"),("temperature_2m",None)]:
            data = json.loads(w.fixture("Tashkent"))
            data["current"][key] = bad
            self.assertEqual(w.collect(self.db,"Tashkent",getter=lambda url:json.dumps(data).encode()),"error")
        self.assertEqual(self.db.execute("SELECT count(*) FROM weather_readings").fetchone()[0],0)

    def test_retry_and_recovery(self):
        events = [URLError("offline"), w.fixture("Tashkent")]
        def fetch(url):
            event = events.pop(0)
            if isinstance(event,Exception): raise event
            return event
        self.assertEqual(w.collect(self.db,"Tashkent",getter=fetch,pause=lambda seconds:None),"saved")
        self.assertEqual(self.db.execute("SELECT status FROM collection_runs ORDER BY id").fetchall(),[("retry",),("saved",)])

    def test_raw_responses_are_kept(self):
        w.collect(self.db,"Tashkent",True)
        w.collect(self.db,"Tashkent",True)
        bad = json.loads(w.fixture("Tashkent"))
        bad["current"]["wind_speed_10m"] = -1
        w.collect(self.db,"Tashkent",getter=lambda url:json.dumps(bad).encode())
        rows = self.db.execute("SELECT r.status,x.body FROM collection_runs r JOIN raw_responses x ON x.run_id=r.id ORDER BY r.id").fetchall()
        self.assertEqual([s for s,_ in rows],["saved","duplicate","error"])
        self.assertEqual(rows[0][1],w.fixture("Tashkent"))

    def test_revision_is_logged_and_original_reading_kept(self):
        w.collect(self.db,"Tashkent",True)
        changed = json.loads(w.fixture("Tashkent"))
        changed["current"]["temperature_2m"] = 25.5
        self.assertEqual(w.collect(self.db,"Tashkent",getter=lambda url:json.dumps(changed).encode()),"revision")
        self.assertEqual(self.db.execute("SELECT temp_c FROM weather_readings").fetchall(),[(18,)])
        self.assertEqual(self.db.execute("SELECT count(*) FROM raw_responses").fetchone()[0],2)

    def test_collection_window(self):
        original = w.COLLECTION_START
        self.addCleanup(setattr, w, "COLLECTION_START", original)
        at = lambda d, hour_utc, minute=0: datetime(2026, 11, d, hour_utc, minute, tzinfo=timezone.utc)
        w.COLLECTION_START = None
        self.assertIsNotNone(w.window_problem(at(5, 5)))
        w.COLLECTION_START = date(2026, 11, 5)
        self.assertIsNone(w.window_problem(at(5, 3)))          # 08:00 Tashkent, day 1
        self.assertIsNone(w.window_problem(at(25, 10, 40)))    # 15:40 Tashkent, day 21 (late 15:00 run)
        self.assertIsNotNone(w.window_problem(at(5, 2, 59)))   # 07:59 Tashkent
        self.assertIsNotNone(w.window_problem(at(5, 11)))      # 16:00 Tashkent
        self.assertIsNotNone(w.window_problem(at(4, 5)))       # day before start
        self.assertIsNotNone(w.window_problem(at(26, 5)))      # day 22

    def test_one_batch_per_hour_keeps_partial_success(self):
        def flaky(url):
            if "39.77" in url:                                  # Bukhara fails on the first run
                raise ValueError("server error")
            return w.fixture("Samarkand" if "39.65" in url else "Tashkent")
        now = datetime.now(timezone.utc)
        first = w.run_live(self.db, now, getter=flaky)
        self.assertEqual(first, {"Tashkent":"saved","Samarkand":"saved","Bukhara":"error"})
        second = w.run_live(self.db, now, getter=lambda url: w.fixture("Bukhara"))
        self.assertTrue(second["Tashkent"].startswith("skipped"))
        self.assertTrue(second["Samarkand"].startswith("skipped"))
        self.assertEqual(second["Bukhara"], "saved")
        self.assertEqual(self.db.execute("SELECT count(*) FROM weather_readings").fetchone()[0], 3)

if __name__ == "__main__":
    unittest.main()
