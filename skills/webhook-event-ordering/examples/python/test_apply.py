"""Runs against a real PostgreSQL: set WEBHOOK_TEST_DATABASE_URL. Each run works in its own schema.

    python -m unittest -v test_apply.py
"""

import os
import random
import secrets
import threading
import unittest

import psycopg

from apply import SCHEMA_SQL, apply_event

URL = os.environ.get("WEBHOOK_TEST_DATABASE_URL")
if not URL:
    raise RuntimeError("Set WEBHOOK_TEST_DATABASE_URL to a PostgreSQL database these tests may create a schema in.")
SCHEMA = "order_test_" + secrets.token_hex(6)


def connect():
    return psycopg.connect(URL, autocommit=True, options=f"-c search_path={SCHEMA}")


def setUpModule():
    with psycopg.connect(URL, autocommit=True) as admin:
        admin.execute(f"CREATE SCHEMA {SCHEMA}")
    with connect() as conn:
        conn.execute(SCHEMA_SQL)


def tearDownModule():
    with psycopg.connect(URL, autocommit=True) as admin:
        admin.execute(f"DROP SCHEMA {SCHEMA} CASCADE")


def row(cid):
    with connect() as conn:
        return conn.execute("SELECT email, plan, deleted, version FROM customers WHERE customer_id = %s", (cid,)).fetchone()


def upsert(cid, version, plan, email="x@example.test"):
    return {"customerId": cid, "version": version, "type": "upserted", "email": email, "plan": plan}


class ApplyEvent(unittest.TestCase):
    def setUp(self):
        self.conn = connect()

    def tearDown(self):
        self.conn.close()

    def test_events_in_order_are_all_applied(self):
        self.assertEqual(apply_event(self.conn, upsert("c1", 1, "free")), "applied")
        self.assertEqual(apply_event(self.conn, upsert("c1", 2, "pro")), "applied")
        self.assertEqual(row("c1")[1], "pro")

    def test_an_older_event_arriving_late_does_not_overwrite_newer_state(self):
        apply_event(self.conn, upsert("c2", 5, "pro", "new@example.test"))
        self.assertEqual(apply_event(self.conn, upsert("c2", 3, "free", "old@example.test")), "stale")
        self.assertEqual(row("c2"), ("new@example.test", "pro", False, 5))

    def test_a_redelivery_of_the_same_version_changes_nothing(self):
        apply_event(self.conn, upsert("c3", 1, "free"))
        self.assertEqual(apply_event(self.conn, upsert("c3", 1, "free")), "stale")

    def test_a_delete_leaves_a_tombstone_a_late_update_cannot_resurrect(self):
        apply_event(self.conn, upsert("c4", 1, "pro"))
        self.assertEqual(apply_event(self.conn, {"customerId": "c4", "version": 3, "type": "deleted"}), "applied")
        self.assertEqual(apply_event(self.conn, upsert("c4", 2, "pro")), "stale")
        self.assertTrue(row("c4")[2])

    def test_a_delete_arriving_before_the_create_still_wins(self):
        self.assertEqual(apply_event(self.conn, {"customerId": "c5", "version": 2, "type": "deleted"}), "applied")
        self.assertEqual(apply_event(self.conn, upsert("c5", 1, "free")), "stale")
        self.assertTrue(row("c5")[2])

    def test_twenty_events_applied_concurrently_in_random_order_settle_on_the_newest(self):
        events = [upsert("c6", i, f"plan-{i}", "c6@example.test") for i in range(1, 21)]
        random.shuffle(events)

        def deliver(e):
            with connect() as conn:
                apply_event(conn, e)

        threads = [threading.Thread(target=deliver, args=(e,)) for e in events]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(row("c6"), ("c6@example.test", "plan-20", False, 20))


if __name__ == "__main__":
    unittest.main()
