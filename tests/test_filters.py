import sys
from datetime import datetime
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from session_viewer import (
    build_search_tokens,
    update_search_hits,
    matches_project_filter,
    matches_date_range,
    parse_datetime_input,
)


class FilterHelpersTestCase(unittest.TestCase):
    def test_build_search_tokens(self):
        self.assertEqual(build_search_tokens("  Foo  bar "), ["foo", "bar"])
        self.assertEqual(build_search_tokens(""), [])

    def test_update_search_hits(self):
        tokens = ["foo", "bar"]
        found = set()
        self.assertFalse(update_search_hits(tokens, found, "foo only"))
        self.assertIn("foo", found)
        self.assertTrue(update_search_hits(tokens, found, "BAR here"))
        self.assertEqual(found, {"foo", "bar"})

    def test_matches_project_filter(self):
        self.assertTrue(matches_project_filter("/Users/zbs/Project", "users"))
        self.assertTrue(matches_project_filter("/Users/zbs/Project", "PROJECT"))
        self.assertFalse(matches_project_filter("/Users/zbs/Project", "missing"))

    def test_matches_date_range(self):
        start_time = datetime(2026, 1, 14, 10, 0)
        since = datetime(2026, 1, 1, 0, 0)
        until = datetime(2026, 1, 31, 0, 0)
        self.assertTrue(matches_date_range(start_time, since, until))
        self.assertFalse(matches_date_range(start_time, datetime(2026, 2, 1, 0, 0), None))
        self.assertFalse(matches_date_range(None, since, until))
        self.assertTrue(matches_date_range(start_time, None, None))

    def test_parse_datetime_input(self):
        parsed = parse_datetime_input("2026-01-14")
        self.assertEqual(parsed, datetime(2026, 1, 14))
        parsed_end = parse_datetime_input("2026-01-14", end_of_day=True)
        self.assertEqual(parsed_end, datetime(2026, 1, 14, 23, 59, 59))
        with self.assertRaises(ValueError):
            parse_datetime_input("")


if __name__ == "__main__":
    unittest.main()
