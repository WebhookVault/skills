#!/usr/bin/env node
// Lists provider facts whose read date is older than the review window, per provider, and exits
// non-zero when there are any (a release gate; see CONTRIBUTING.md, "Provider facts").
//
//   node tools/stale-facts.mjs                       facts older than 90 days
//   node tools/stale-facts.mjs --days 30             a different window
//   node tools/stale-facts.mjs --as-of 2027-01-31    judge from another date (for planning a re-read)
//
// A stale fact is re-read on the provider's own page and its read date, value and quote updated in
// data/providers/<slug>.json, then node tools/provider-facts.mjs --write.

import { loadProviders } from "./provider-facts.mjs";

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

const days = Number(arg("--days", "90"));
const asOf = arg("--as-of", new Date().toISOString().slice(0, 10));
if (!Number.isInteger(days) || days < 1) { console.log("error    --days must be a whole number of days"); process.exit(2); }
if (!/^\d{4}-\d{2}-\d{2}$/.test(asOf) || Number.isNaN(Date.parse(asOf))) { console.log("error    --as-of must be a YYYY-MM-DD date"); process.exit(2); }

const cutoff = new Date(Date.parse(asOf) - days * 86400000).toISOString().slice(0, 10);

function collect(node, path, out) {
  if (Array.isArray(node)) node.forEach((v, i) => collect(v, `${path}[${i}]`, out));
  else if (node && typeof node === "object") {
    if (typeof node.read === "string" && "source_url" in node) out.push({ path, read: node.read, url: node.source_url });
    for (const [k, v] of Object.entries(node)) if (k !== "read") collect(v, path ? `${path}.${k}` : k, out);
  }
}

let stale = 0;
let total = 0;
const providers = loadProviders();
for (const { slug, data } of providers) {
  const facts = [];
  collect(data, "", facts);
  total += facts.length;
  const old = facts.filter((f) => f.read < cutoff);
  if (old.length === 0) continue;
  stale += old.length;
  const pages = [...new Set(old.map((f) => f.url))];
  console.log(`${slug}: ${old.length} of ${facts.length} facts read before ${cutoff}; re-read ${pages.length} page(s):`);
  for (const p of pages) console.log(`  ${p}`);
  for (const f of old) console.log(`    ${f.path} (read ${f.read})`);
}

console.log(`${providers.length} provider(s), ${total} facts, ${stale} older than ${days} days as of ${asOf}.`);
process.exit(stale ? 1 : 0);
