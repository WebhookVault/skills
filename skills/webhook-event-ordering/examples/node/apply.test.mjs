// Runs against a real PostgreSQL: set WEBHOOK_TEST_DATABASE_URL. Each run works in its own schema.

import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import pg from "pg";
import { SCHEMA_SQL, applyEvent } from "./apply.mjs";

const url = process.env.WEBHOOK_TEST_DATABASE_URL;
if (!url) throw new Error("Set WEBHOOK_TEST_DATABASE_URL to a PostgreSQL database these tests may create a schema in.");
const schema = "order_test_" + crypto.randomBytes(6).toString("hex");
const pool = new pg.Pool({ connectionString: url, max: 10, options: `-c search_path=${schema}` });

async function admin(sql) {
  const c = new pg.Client({ connectionString: url });
  await c.connect();
  await c.query(sql);
  await c.end();
}
before(async () => { await admin(`CREATE SCHEMA ${schema}`); await pool.query(SCHEMA_SQL); });
after(async () => { await pool.end(); await admin(`DROP SCHEMA ${schema} CASCADE`); });

const row = async (id) => (await pool.query("SELECT email, plan, deleted, version FROM customers WHERE customer_id = $1", [id])).rows[0];

test("events in order are all applied", async () => {
  assert.equal(await applyEvent(pool, { customerId: "c1", version: 1, type: "upserted", email: "a@example.test", plan: "free" }), "applied");
  assert.equal(await applyEvent(pool, { customerId: "c1", version: 2, type: "upserted", email: "a@example.test", plan: "pro" }), "applied");
  assert.equal((await row("c1")).plan, "pro");
});

test("an older event arriving late does not overwrite newer state", async () => {
  await applyEvent(pool, { customerId: "c2", version: 5, type: "upserted", email: "new@example.test", plan: "pro" });
  assert.equal(await applyEvent(pool, { customerId: "c2", version: 3, type: "upserted", email: "old@example.test", plan: "free" }), "stale");
  assert.deepEqual(await row("c2"), { email: "new@example.test", plan: "pro", deleted: false, version: "5" });
});

test("a redelivery of the same version changes nothing", async () => {
  await applyEvent(pool, { customerId: "c3", version: 1, type: "upserted", email: "x@example.test", plan: "free" });
  assert.equal(await applyEvent(pool, { customerId: "c3", version: 1, type: "upserted", email: "x@example.test", plan: "free" }), "stale");
});

test("a delete leaves a tombstone that a late update cannot resurrect", async () => {
  await applyEvent(pool, { customerId: "c4", version: 1, type: "upserted", email: "d@example.test", plan: "pro" });
  assert.equal(await applyEvent(pool, { customerId: "c4", version: 3, type: "deleted" }), "applied");
  assert.equal(await applyEvent(pool, { customerId: "c4", version: 2, type: "upserted", email: "d@example.test", plan: "pro" }), "stale");
  assert.equal((await row("c4")).deleted, true);
});

test("a delete arriving before the create still wins", async () => {
  assert.equal(await applyEvent(pool, { customerId: "c5", version: 2, type: "deleted" }), "applied");
  assert.equal(await applyEvent(pool, { customerId: "c5", version: 1, type: "upserted", email: "e@example.test", plan: "free" }), "stale");
  assert.equal((await row("c5")).deleted, true);
});

test("twenty events applied concurrently in random order settle on the newest", async () => {
  const events = Array.from({ length: 20 }, (_, i) => ({ customerId: "c6", version: i + 1, type: "upserted", email: "c6@example.test", plan: `plan-${i + 1}` }));
  events.sort(() => Math.random() - 0.5);
  await Promise.all(events.map((e) => applyEvent(pool, e)));
  assert.deepEqual(await row("c6"), { email: "c6@example.test", plan: "plan-20", deleted: false, version: "20" });
});
