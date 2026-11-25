import unittest
from streamlit.testing.v1 import AppTest


class DashboardTests(unittest.TestCase):
    def test_dashboard_runs_and_shows_all_five_tabs(self):
        app = AppTest.from_file("dashboard.py", default_timeout=60).run()
        self.assertFalse(app.exception, [e.value for e in app.exception])
        self.assertEqual([t.label for t in app.tabs],
                         ["Overview", "City comparison", "History", "Collection quality", "Next-hour estimate"])
        labels = [m.label for m in app.metric]
        self.assertIn("Unique records", labels)


if __name__ == "__main__":
    unittest.main()
