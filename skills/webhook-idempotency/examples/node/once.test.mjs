// Runs against a real PostgreSQL: set WEBHOOK_TEST_DATABASE_URL (for example
// postgres://user:password@localhost:5432/scratch). Each run works in its own schema and drops it.

import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import pg from "pg";
import { SCHEMA_SQL, processOnce, forgetOlderThan } from "./once.mjs";

const url = process.env.WEBHOOK_TEST_DATABASE_URL;
if (!url) throw new Error("Set WEBHOOK_TEST_DATABASE_URL to a PostgreSQL database these tests may create a schema in.");

const schema = "idem_test_" + crypto.randomBytes(6).toString("hex");
const pool = new pg.Pool({ connectionString: url, max: 10, options: `-c search_path=${schema}` });

before(async () => {
  const admin = new pg.Client({ connectionString: url });
  await admin.connect();
  await admin.query(`CREATE SCHEMA ${schema}`);
  await admin.end();
  await pool.query(SCHEMA_SQL);
  await pool.query("CREATE TABLE orders (order_id text PRIMARY KEY, event_id text NOT NULL)");
});

after(async () => {
  await pool.end();
  const admin = new pg.Client({ connectionString: url });
  await admin.connect();
  await admin.query(`DROP SCHEMA ${schema} CASCADE`);
  await admin.end();
});

const createOrder = (orderId, eventId) => (client) =>
  client.query("INSERT INTO orders (order_id, event_id) VALUES ($1, $2)", [orderId, eventId]);
const count = async (sql, params = []) => Number((await pool.query(sql, params)).rows[0].n);

test("the first delivery is processed and a redelivery is a duplicate", async () => {
  assert.equal(await processOnce(pool, "shop", "evt_test_1", createOrder("ord_1", "evt_test_1")), "processed");
  assert.equal(await processOnce(pool, "shop", "evt_test_1", createOrder("ord_1b", "evt_test_1")), "duplicate");
  assert.equal(await count("SELECT count(*) AS n FROM orders WHERE event_id = $1", ["evt_test_1"]), 1);
});

test("the same id from two senders is two events", async () => {
  assert.equal(await processOnce(pool, "shop", "evt_test_2", createOrder("ord_2a", "evt_test_2")), "processed");
  assert.equal(await processOnce(pool, "billing", "evt_test_2", createOrder("ord_2b", "evt_test_2")), "processed");
});

test("a failed handler leaves nothing behind and the retry processes it", async () => {
  await assert.rejects(processOnce(pool, "shop", "evt_test_3", async (client) => {
    await createOrder("ord_3", "evt_test_3")(client);
    throw new Error("downstream failed");
  }));
  assert.equal(await count("SELECT count(*) AS n FROM orders WHERE order_id = 'ord_3'"), 0);
  assert.equal(await count("SELECT count(*) AS n FROM webhook_events WHERE event_id = 'evt_test_3'"), 0);
  assert.equal(await processOnce(pool, "shop", "evt_test_3", createOrder("ord_3", "evt_test_3")), "processed");
});

test("ten copies arriving at once run the handler exactly once", async () => {
  let runs = 0;
  const handler = async (client) => {
    runs++;
    await client.query("SELECT pg_sleep(0.05)");
    await createOrder("ord_4", "evt_test_4")(client);
  };
  const results = await Promise.all(Array.from({ length: 10 }, () => processOnce(pool, "shop", "evt_test_4", handler)));
  assert.equal(results.filter((r) => r === "processed").length, 1);
  assert.equal(results.filter((r) => r === "duplicate").length, 9);
  assert.equal(runs, 1);
  assert.equal(await count("SELECT count(*) AS n FROM orders WHERE order_id = 'ord_4'"), 1);
});

test("old claims can be forgotten", async () => {
  await pool.query("INSERT INTO webhook_events (source, event_id, received_at) VALUES ('shop', 'evt_test_old', now() - interval '40 days')");
  assert.ok(await forgetOlderThan(pool, 30) >= 1);
  assert.equal(await count("SELECT count(*) AS n FROM webhook_events WHERE event_id = 'evt_test_old'"), 0);
  assert.equal(await count("SELECT count(*) AS n FROM webhook_events WHERE event_id = 'evt_test_1'"), 1);
});
