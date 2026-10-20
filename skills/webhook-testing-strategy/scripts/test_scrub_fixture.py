"""python -m unittest -v test_scrub_fixture.py (run from this folder)"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

from scrub_fixture import scrub, scrub_string


class Scrub(unittest.TestCase):
    def test_emails_phones_and_long_digit_runs_are_replaced(self):
        self.assertEqual(scrub_string("mail jane.doe+shop@mail.example.com now"), "mail person@example.test now")
        self.assertEqual(scrub_string("call +1 (415) 555-2671"), "call +15550100")
        self.assertEqual(scrub_string("card 4111111111111111"), "card 0000000000000000")

    def test_short_numbers_ids_and_dates_are_kept(self):
        for kept in ("order 1234", "2026-10-20T12:00:00Z", "evt_1NxYz", "v2.3.1", "qty 3", "ord_9f8e7d"):
            self.assertEqual(scrub_string(kept), kept)

    def test_structure_keys_and_non_strings_are_kept(self):
        given = {"id": "evt_test_1", "amount": 4900, "paid": True, "customer": {"email": "a@b.example", "phone": None},
                 "items": [{"sku": "SKU-1", "note": "ring 0821234567 please"}]}
        self.assertEqual(scrub(given), {"id": "evt_test_1", "amount": 4900, "paid": True,
                                        "customer": {"email": "person@example.test", "phone": None},
                                        "items": [{"sku": "SKU-1", "note": "ring +15550100 please"}]})

    def test_the_command_line_writes_scrubbed_json(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"email": "x@y.example", "n": 1}, f)
        try:
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scrub_fixture.py")
            out = subprocess.run([sys.executable, script, f.name], capture_output=True, text=True, check=True).stdout
        finally:
            os.unlink(f.name)
        self.assertEqual(json.loads(out), {"email": "person@example.test", "n": 1})


if __name__ == "__main__":
    unittest.main()
