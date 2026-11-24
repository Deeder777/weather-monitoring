import sqlite3
import unittest
import models as m
import weather as w


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.db = w.connect(":memory:")
        self.addCleanup(self.db.close)
        self.run_id = self.db.execute("INSERT INTO collection_runs VALUES(NULL,'Tashkent','2026-11-02T03:01:00+00:00','test',NULL,'saved',NULL)").lastrowid

    def add(self, stamp, temp, city="Tashkent"):
        self.db.execute("INSERT INTO weather_readings VALUES(?,?,?,50,5,950,?)", (city, stamp, temp, self.run_id))

    def test_pairs_use_later_reading_and_only_past_information(self):
        self.add("2026-11-02T03:00Z", 10.0)   # 08:00 Tashkent
        self.add("2026-11-02T04:00Z", 12.0)   # 09:00
        self.add("2026-11-02T05:15Z", 14.0)   # 10:15: not exactly 60 min after 09:00
        pairs = m.load_pairs(self.db)
        self.assertEqual(len(pairs), 1)
        p = pairs[0]
        self.assertEqual((p["hour"], p["temp"], p["target"]), (8, 10.0, 12.0))
        self.assertEqual((p["change"], p["no_previous"]), (0.0, 1))    # nothing before 08:00
        x = m.features(pairs, "temperature_history")[0]
        self.assertNotIn(12.0, list(x))                               # the answer is not a feature

    def test_validation_windows_never_touch_test_days(self):
        for train_days, val_days in m.WINDOWS:
            used = m.days(train_days) | m.days(val_days)
            self.assertTrue(used <= set(m.DEV_DAYS))
            self.assertLess(max(train_days), min(val_days))          # train strictly before validation
        self.assertFalse(set(m.DEV_DAYS) & set(m.TEST_DAYS))


if __name__ == "__main__":
    unittest.main()
