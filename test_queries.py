import unittest
import queries as q
import weather as w


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.db = w.connect(":memory:")
        self.addCleanup(self.db.close)
        run = self.db.execute("INSERT INTO collection_runs VALUES(NULL,'Tashkent','2026-11-02T03:01:00+00:00','test',NULL,'saved',NULL)").lastrowid
        self.run_id = run

    def add(self, city, stamp, temp):
        self.db.execute("INSERT INTO weather_readings VALUES(?,?,?,50,5,950,?)", (city, stamp, temp, self.run_id))

    def test_prediction_pairs_need_exactly_one_hour_and_same_city(self):
        self.add("Tashkent", "2026-11-02T03:00Z", 10)
        self.add("Tashkent", "2026-11-02T04:00Z", 11)   # pair with 03:00
        self.add("Tashkent", "2026-11-02T05:15Z", 12)   # 75 min later: no pair
        self.add("Samarkand", "2026-11-02T05:00Z", 9)   # other city: no pair
        self.add("Bukhara", "2026-11-18T03:00Z", 8)
        self.add("Bukhara", "2026-11-18T04:00Z", 9)     # test-day pair
        _, rows = q.run(self.db, 5)
        self.assertEqual(rows, [("Tashkent", "development", 1), ("Bukhara", "test", 1)])

    def test_city_difference_requires_six_matched_hours(self):
        for hour in range(3, 9):                       # 6 matched hours on 2 Nov
            self.add("Tashkent", f"2026-11-02T{hour:02d}:00Z", 12)
            self.add("Samarkand", f"2026-11-02T{hour:02d}:00Z", 10)
        for hour in range(3, 8):                       # only 5 matched hours on 3 Nov
            self.add("Tashkent", f"2026-11-03T{hour:02d}:00Z", 12)
            self.add("Samarkand", f"2026-11-03T{hour:02d}:00Z", 10)
        _, rows = q.run(self.db, 4)
        self.assertEqual(rows, [("2026-11-02", 6, 2.0)])


if __name__ == "__main__":
    unittest.main()
