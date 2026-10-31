import json
import unittest
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

if __name__ == "__main__":
    unittest.main()
