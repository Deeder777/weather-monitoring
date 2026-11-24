import unittest
import compare_cities as cc
import weather as w


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.db = w.connect(":memory:")
        self.addCleanup(self.db.close)
        self.run_id = self.db.execute("INSERT INTO collection_runs VALUES(NULL,'Tashkent','2026-11-02T03:01:00+00:00','test',NULL,'saved',NULL)").lastrowid

    def add(self, city, stamp, temp):
        self.db.execute("INSERT INTO weather_readings VALUES(?,?,?,50,5,950,?)", (city, stamp, temp, self.run_id))

    def test_complete_days_need_all_eight_on_the_hour_matches(self):
        for hour in range(3, 11):                      # 2 Nov: 8 on-the-hour matched hours
            self.add("Tashkent", f"2026-11-02T{hour:02d}:00Z", 12)
            self.add("Samarkand", f"2026-11-02T{hour:02d}:00Z", 11)
        for hour in range(3, 10):                      # 3 Nov: 7 on the hour + one at :15
            self.add("Tashkent", f"2026-11-03T{hour:02d}:00Z", 10)
            self.add("Samarkand", f"2026-11-03T{hour:02d}:00Z", 12)
        self.add("Tashkent", "2026-11-03T10:15Z", 10)
        self.add("Samarkand", "2026-11-03T10:15Z", 12)
        self.assertEqual(cc.daily_differences(self.db), [("2026-11-02", 8, 1.0), ("2026-11-03", 8, -2.0)])
        self.assertEqual(cc.daily_differences(self.db, complete_only=True), [("2026-11-02", 8, 1.0)])

    def test_bootstrap_is_reproducible_and_contains_the_mean(self):
        values = [0.5, -1.0, 1.2, 0.3, -0.4, 0.8, 1.5, -0.2, 0.1, 0.6]
        first, second = cc.block_bootstrap(values, 1), cc.block_bootstrap(values, 1)
        self.assertEqual(list(first), list(second))
        self.assertLess(first[0], sum(values) / len(values))
        self.assertGreater(first[1], sum(values) / len(values))


if __name__ == "__main__":
    unittest.main()
