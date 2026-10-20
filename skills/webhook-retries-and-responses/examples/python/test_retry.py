"""python -m unittest -v test_retry.py"""

import unittest
from email.utils import parsedate_to_datetime

from retry import backoff_delay, deliver_with_retries, is_retryable_status, parse_retry_after

# RFC 9110's own example of an HTTP-date.
RFC_DATE = "Wed, 21 Oct 2015 07:28:00 GMT"
NOW = int(parsedate_to_datetime("Wed, 21 Oct 2015 07:27:00 GMT").timestamp() * 1000)


def script(*answers):
    state = {"i": 0}

    def send():
        a = answers[min(state["i"], len(answers) - 1)]
        state["i"] += 1
        if a == "throw":
            raise ConnectionError("connection reset")
        return a if isinstance(a, tuple) else (a, {})
    return send


class Clock:
    def __init__(self):
        self.t, self.waits = 0, []

    def now(self):
        return self.t

    def sleep(self, ms):
        self.waits.append(ms)
        self.t += ms


class Retry(unittest.TestCase):
    def test_only_statuses_that_can_succeed_later_are_retried(self):
        for s in (408, 425, 429, 500, 502, 503, 504, 599):
            self.assertTrue(is_retryable_status(s), s)
        for s in (200, 301, 400, 401, 403, 404, 409, 410, 413, 422):
            self.assertFalse(is_retryable_status(s), s)

    def test_backoff_doubles_under_the_cap_with_full_jitter(self):
        top = lambda: 0.999999  # noqa: E731
        self.assertEqual(backoff_delay(0, 1000, random=top), 999)
        self.assertEqual(backoff_delay(3, 1000, random=top), 7999)
        self.assertEqual(backoff_delay(30, 1000, 60_000, random=top), 59_999)
        self.assertEqual(backoff_delay(5, random=lambda: 0), 0)
        with self.assertRaises(ValueError):
            backoff_delay(-1)

    def test_retry_after_reads_seconds_and_the_http_date_only(self):
        self.assertEqual(parse_retry_after("120", NOW), 120_000)
        self.assertEqual(parse_retry_after(" 0 ", NOW), 0)
        self.assertEqual(parse_retry_after(RFC_DATE, NOW), 60_000)
        self.assertEqual(parse_retry_after("Wed, 21 Oct 2015 07:26:00 GMT", NOW), 0)
        for bad in ("-5", "1.5", "tomorrow", None):
            self.assertIsNone(parse_retry_after(bad, NOW), bad)

    def test_a_receiver_that_recovers_is_delivered_after_retries(self):
        c = Clock()
        self.assertEqual(deliver_with_retries(script(503, "throw", 200), random=lambda: 0.5, sleep=c.sleep, now=c.now), ("delivered", 3, 200))
        self.assertEqual(c.waits, [500, 1000])

    def test_a_permanent_answer_stops_at_once(self):
        c = Clock()
        self.assertEqual(deliver_with_retries(script(400), sleep=c.sleep, now=c.now), ("rejected", 1, 400))
        self.assertEqual(c.waits, [])

    def test_retry_after_is_honoured_instead_of_the_backoff(self):
        c = Clock()
        result = deliver_with_retries(script((429, {"retry-after": "7"}), 200), random=lambda: 0.5, sleep=c.sleep, now=c.now)
        self.assertEqual(result[0], "delivered")
        self.assertEqual(c.waits, [7000])

    def test_the_attempt_budget_ends_in_a_dead_letter(self):
        c = Clock()
        self.assertEqual(deliver_with_retries(script(500), max_attempts=4, random=lambda: 0, sleep=c.sleep, now=c.now), ("dead_letter", 4, 500))
        self.assertEqual(len(c.waits), 3)

    def test_the_time_budget_ends_the_attempts_early(self):
        c = Clock()
        result = deliver_with_retries(script((503, {"retry-after": "7200"})), max_elapsed_ms=3_600_000, sleep=c.sleep, now=c.now)
        self.assertEqual(result, ("dead_letter", 1, 503))
        self.assertEqual(c.waits, [])


if __name__ == "__main__":
    unittest.main()
