"""Runs against a real PostgreSQL: set WEBHOOK_TEST_DATABASE_URL (for example
postgres://user:password@localhost:5432/scratch). Each run works in its own schema and drops it.

    python -m unittest -v test_once.py
"""

import os
import secrets
import threading
import time
import unittest

import psycopg

from once import SCHEMA_SQL, forget_older_than, process_once

URL = os.environ.get("WEBHOOK_TEST_DATABASE_URL")
if not URL:
    raise RuntimeError("Set WEBHOOK_TEST_DATABASE_URL to a PostgreSQL database these tests may create a schema in.")

SCHEMA = "idem_test_" + secrets.token_hex(6)


def connect():
    # autocommit, so each process_once() call's transaction() block is the whole transaction.
    return psycopg.connect(URL, autocommit=True, options=f"-c search_path={SCHEMA}")


def setUpModule():
    with psycopg.connect(URL, autocommit=True) as admin:
        admin.execute(f"CREATE SCHEMA {SCHEMA}")
    with connect() as conn:
        conn.execute(SCHEMA_SQL)
        conn.execute("CREATE TABLE orders (order_id text PRIMARY KEY, event_id text NOT NULL)")


def tearDownModule():
    with psycopg.connect(URL, autocommit=True) as admin:
        admin.execute(f"DROP SCHEMA {SCHEMA} CASCADE")


def create_order(order_id, event_id):
    return lambda conn: conn.execute("INSERT INTO orders (order_id, event_id) VALUES (%s, %s)", (order_id, event_id))


def count(sql, params=()):
    with connect() as conn:
        return conn.execute(sql, params).fetchone()[0]


class ProcessOnce(unittest.TestCase):
    def test_the_first_delivery_is_processed_and_a_redelivery_is_a_duplicate(self):
        with connect() as conn:
            self.assertEqual(process_once(conn, "shop", "evt_test_1", create_order("ord_1", "evt_test_1")), "processed")
            self.assertEqual(process_once(conn, "shop", "evt_test_1", create_order("ord_1b", "evt_test_1")), "duplicate")
        self.assertEqual(count("SELECT count(*) FROM orders WHERE event_id = %s", ("evt_test_1",)), 1)

    def test_the_same_id_from_two_senders_is_two_events(self):
        with connect() as conn:
            self.assertEqual(process_once(conn, "shop", "evt_test_2", create_order("ord_2a", "evt_test_2")), "processed")
            self.assertEqual(process_once(conn, "billing", "evt_test_2", create_order("ord_2b", "evt_test_2")), "processed")

    def test_a_failed_handler_leaves_nothing_behind_and_the_retry_processes_it(self):
        def failing(conn):
            create_order("ord_3", "evt_test_3")(conn)
            raise RuntimeError("downstream failed")

        with connect() as conn:
            with self.assertRaises(RuntimeError):
                process_once(conn, "shop", "evt_test_3", failing)
            self.assertEqual(count("SELECT count(*) FROM orders WHERE order_id = 'ord_3'"), 0)
            self.assertEqual(count("SELECT count(*) FROM webhook_events WHERE event_id = 'evt_test_3'"), 0)
            self.assertEqual(process_once(conn, "shop", "evt_test_3", create_order("ord_3", "evt_test_3")), "processed")

    def test_ten_copies_arriving_at_once_run_the_handler_exactly_once(self):
        runs, results, lock = [], [], threading.Lock()

        def handler(conn):
            with lock:
                runs.append(1)
            time.sleep(0.05)
            create_order("ord_4", "evt_test_4")(conn)

        def deliver():
            with connect() as conn:
                result = process_once(conn, "shop", "evt_test_4", handler)
            with lock:
                results.append(result)

        threads = [threading.Thread(target=deliver) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(results.count("processed"), 1)
        self.assertEqual(results.count("duplicate"), 9)
        self.assertEqual(len(runs), 1)
        self.assertEqual(count("SELECT count(*) FROM orders WHERE order_id = 'ord_4'"), 1)

    def test_old_claims_can_be_forgotten(self):
        with connect() as conn:
            conn.execute("INSERT INTO webhook_events (source, event_id, received_at) VALUES ('shop', 'evt_test_old', now() - interval '40 days')")
            conn.execute("INSERT INTO webhook_events (source, event_id) VALUES ('shop', 'evt_test_new') ON CONFLICT DO NOTHING")
            self.assertGreaterEqual(forget_older_than(conn, 30), 1)
        self.assertEqual(count("SELECT count(*) FROM webhook_events WHERE event_id = 'evt_test_old'"), 0)
        self.assertEqual(count("SELECT count(*) FROM webhook_events WHERE event_id = 'evt_test_new'"), 1)


if __name__ == "__main__":
    unittest.main()
