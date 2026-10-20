#!/usr/bin/env node
// Checks the provider facts in data/providers/<slug>.json and data/webhookvault-presets.json, and
// renders them into each provider skill: references/facts.md (every fact with its source page, read
// date and quote) and the quick-facts block in SKILL.md.
//
//   node tools/provider-facts.mjs           check: exits non-zero if a fact is malformed or a skill is out of date
//   node tools/provider-facts.mjs --write   rewrite the generated parts of every provider skill
//
// No dependencies: plain Node 20 or later. validate.mjs runs the check too. Facts are changed in the
// JSON file and regenerated, never edited in a skill (CONTRIBUTING.md, "Provider facts").

import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync } from "node:fs";
import { join, dirname, resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const NOT_STATED = "not stated by the provider";
export const FACTS_START_PREFIX = "<!-- facts:start";
export const FACTS_END = "<!-- facts:end -->";
const factsStart = (slug) => `${FACTS_START_PREFIX} (generated from data/providers/${slug}.json by tools/provider-facts.mjs; edit the data, not this block) -->`;

// Every fact a provider file must carry, by section. A value may be NOT_STATED, never missing.
const REQUIRED = {
  signature: ["header", "scheme", "signed_content", "header_format", "secret_source", "secret_scope", "timestamp_tolerance", "rotation", "raw_body_note"],
  delivery: ["method_and_content_type", "event_type_location", "delivery_id", "handshake", "batching"],
  responding: ["success_status", "response_deadline", "retries", "disabling", "ordering", "duplicates"],
  setup: ["where_url_is_entered", "test_tools", "ip_allowlist"],
};

const LABELS = {
  header: "Signature header",
  scheme: "Scheme",
  signed_content: "Signed content",
  header_format: "Header format",
  secret_source: "Where the secret comes from",
  secret_scope: "Secret scope",
  timestamp_tolerance: "Timestamp tolerance",
  rotation: "Secret rotation",
  raw_body_note: "Raw body",
  method_and_content_type: "Method and content type",
  event_type_location: "Event name",
  delivery_id: "Delivery or event id",
  handshake: "Handshake",
  batching: "Events per request",
  success_status: "Expected response",
  response_deadline: "Response deadline",
  retries: "Retries",
  disabling: "Disabling after failures",
  ordering: "Ordering",
  duplicates: "Duplicates",
  where_url_is_entered: "Where the URL goes",
  test_tools: "Test tools",
  ip_allowlist: "Source IP addresses",
  node: "Node.js",
  python: "Python",
  dotnet: ".NET",
};

// The rows of the quick-facts table in SKILL.md, in order.
const QUICK = [
  ["signature", "header"], ["signature", "scheme"], ["signature", "signed_content"], ["signature", "secret_source"],
  ["signature", "timestamp_tolerance"], ["delivery", "event_type_location"], ["delivery", "delivery_id"],
  ["delivery", "handshake"], ["responding", "success_status"], ["responding", "response_deadline"], ["responding", "retries"],
];

const today = () => new Date().toISOString().slice(0, 10);
// "delivery_handshake" inside an extra section reads as the standard "Handshake" label.
const label = (key) => {
  const bare = key.replace(/^(signature|delivery|responding|setup)_/, "");
  return LABELS[key] ?? LABELS[bare] ?? bare.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
};
// Required facts first, then any further fact the research recorded for that section.
const factKeys = (section, obj) => [...REQUIRED[section], ...Object.keys(obj ?? {}).filter((k) => !REQUIRED[section].includes(k) && k !== "sdk_helpers" && k !== "published_test_vector")];
const isFact = (v) => v !== null && typeof v === "object" && !Array.isArray(v) && "value" in v;

// A domains entry is a host ("docs.stripe.com", which also admits its subdomains) or, for shared
// hosts such as GitHub, a host and path prefix ("github.com/stripe/") naming the provider's own org.
function ownSource(u, domains) {
  return domains.some((d) => {
    const slash = d.indexOf("/");
    if (slash < 0) return u.hostname === d || u.hostname.endsWith(`.${d}`);
    return u.hostname === d.slice(0, slash) && u.pathname.toLowerCase().startsWith(d.slice(slash).toLowerCase());
  });
}

function checkConflict(errors, where, c, domains) {
  if (!c?.topic || !c?.note) errors.push(`${where}: needs topic and note`);
  if (!Array.isArray(c?.sources) || c.sources.length === 0) return errors.push(`${where}: needs sources (each a source_url, read and quote)`);
  c.sources.forEach((s, i) => checkFact(errors, `${where}.sources[${i}]`, { value: c.topic, ...s }, domains));
}

function checkFact(errors, where, fact, domains) {
  if (!isFact(fact)) return errors.push(`${where}: not a fact (needs value, source_url, read, quote)`);
  const { value, source_url: url, read, quote } = fact;
  if (value === undefined || value === null || value === "") errors.push(`${where}: empty value (write "${NOT_STATED}" when the provider says nothing)`);
  if (typeof read !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(read) || Number.isNaN(Date.parse(read))) errors.push(`${where}: read must be a YYYY-MM-DD date`);
  else if (read > today()) errors.push(`${where}: read date ${read} is in the future`);
  let parsed = null;
  try { parsed = new URL(url); if (parsed.protocol !== "https:") throw new Error(); } catch { parsed = null; errors.push(`${where}: source_url must be an https URL`); }
  if (parsed && !ownSource(parsed, domains)) errors.push(`${where}: ${parsed.hostname}${parsed.pathname} is not one of the provider's own sources (${domains.join(", ")})`);
  if (!String(value).startsWith(NOT_STATED) && (typeof quote !== "string" || quote.trim().length < 8)) errors.push(`${where}: a stated fact needs the quote it was read from`);
  if ("short" in fact && (typeof fact.short !== "string" || fact.short.trim() === "" || fact.short.length > 140)) errors.push(`${where}: short is the table form of the value, 1 to 140 characters`);
  if (typeof quote === "string" && quote.length > 600) errors.push(`${where}: quote over 600 characters; quote the sentence that matters`);
}

// Top-level keys every provider file may carry; any other key is an extra section of facts that the
// research found and the standard sections have no place for (Stripe's payload formats, Discord's
// interactions endpoint). Extra sections are checked and rendered like the rest, never dropped.
const STANDARD_KEYS = new Set(["slug", "name", "domains", "docs_home", "signature", "delivery", "responding", "events", "setup", "gotchas", "conflicts", "unreadable", "research_notes"]);
const extraSections = (data) => Object.keys(data).filter((k) => !STANDARD_KEYS.has(k));

export function loadProviders() {
  const dir = join(root, "data", "providers");
  const files = existsSync(dir) ? readdirSync(dir).filter((f) => f.endsWith(".json")).sort() : [];
  return files.map((f) => ({ file: join(dir, f), slug: f.slice(0, -5), data: JSON.parse(readFileSync(join(dir, f), "utf8")) }));
}

export function checkProvider({ slug, data }, presets) {
  const errors = [];
  if (data.slug !== slug) errors.push(`slug "${data.slug}" must equal the file name "${slug}"`);
  if (!data.name) errors.push("name is required");
  const domains = data.domains;
  if (!Array.isArray(domains) || domains.length === 0) { errors.push("domains (the provider's own hosts its sources may come from) is required"); return errors; }
  for (const section of Object.keys(REQUIRED)) {
    for (const key of factKeys(section, data[section])) checkFact(errors, `${section}.${key}`, data[section]?.[key], domains);
  }
  for (const [lang, fact] of Object.entries(data.signature?.sdk_helpers ?? {})) checkFact(errors, `signature.sdk_helpers.${lang}`, fact, domains);
  if (data.signature?.published_test_vector != null) checkFact(errors, "signature.published_test_vector", data.signature.published_test_vector, domains);
  try { new URL(data.events?.full_list_url); } catch { errors.push("events.full_list_url must be a URL"); }
  const common = data.events?.common;
  if (!Array.isArray(common) || common.length < 3) errors.push("events.common needs at least three events");
  else common.forEach((e, i) => { checkFact(errors, `events.common[${i}]`, e, domains); if (!e.meaning) errors.push(`events.common[${i}]: meaning is required`); });
  for (const [key, v] of Object.entries(data.events ?? {})) {
    if (key === "full_list_url" || key === "common") continue;
    if (typeof v === "string") continue; // a note in our own words, shown as such
    checkFact(errors, `events.${key}`, v, domains);
  }
  (data.gotchas ?? []).forEach((g, i) => checkFact(errors, `gotchas[${i}]`, g, domains));
  (data.conflicts ?? []).forEach((c, i) => checkConflict(errors, `conflicts[${i}]`, c, domains));
  for (const key of extraSections(data)) {
    const section = data[key];
    if (section === null || typeof section !== "object" || Array.isArray(section)) { errors.push(`${key}: an extra section must be a map of facts`); continue; }
    for (const [k, v] of Object.entries(section)) {
      if (Array.isArray(v)) v.forEach((f, i) => checkFact(errors, `${key}.${k}[${i}]`, f, domains));
      else checkFact(errors, `${key}.${k}`, v, domains);
    }
  }
  if (data.research_notes !== undefined && (!Array.isArray(data.research_notes) || data.research_notes.some((n) => typeof n !== "string"))) errors.push("research_notes must be a list of strings");
  for (const u of data.unreadable ?? []) if (!u.url || !u.why) errors.push("unreadable entries need url and why");
  if (!presets.providers[slug]) errors.push(`no entry in data/webhookvault-presets.json for ${slug}`);
  return errors;
}

// ---- rendering ------------------------------------------------------------------------------

// Quotes are verbatim, except long dashes, which this repository never prints (CONTRIBUTING.md).
const LONG_DASH = new RegExp(`\\s*[${String.fromCharCode(0x2013, 0x2014)}]\\s*`, "g");
const clean = (s) => String(s).replace(LONG_DASH, " - ").replace(/\s+/g, " ").trim();
const cell = (s) => clean(s).replace(/\|/g, "\\|");
const show = (value) => Array.isArray(value) ? value.map(clean).join("; ") : typeof value === "object" ? null : clean(value);

function renderFact(label, fact) {
  if (fact == null) return [];
  const out = [];
  const shown = show(fact.value);
  if (shown === null) {
    out.push(`- **${label}:**`, "", "  ```json", ...JSON.stringify(fact.value, null, 2).split("\n").map((l) => `  ${l}`), "  ```", "");
  } else {
    out.push(`- **${label}:** ${shown}`);
  }
  const source = `[${new URL(fact.source_url).hostname}${new URL(fact.source_url).pathname}](${fact.source_url})`;
  out.push(fact.quote ? `  Read ${fact.read} from ${source}: "${clean(fact.quote)}"` : `  Checked ${fact.read} at ${source}.`);
  return out;
}

function readRange(data) {
  const dates = [];
  JSON.stringify(data, (k, v) => { if (k === "read" && typeof v === "string") dates.push(v); return v; });
  dates.sort();
  return dates.length === 0 ? "" : dates[0] === dates.at(-1) ? dates[0] : `${dates[0]} to ${dates.at(-1)}`;
}

export function renderFactsMd({ slug, data }, presets) {
  const p = presets.providers[slug];
  const lines = [
    `# ${data.name} webhook facts`,
    "",
    `Generated from \`data/providers/${slug}.json\` by \`tools/provider-facts.mjs\`; change the data and regenerate, never this file.`,
    `Every fact was read from ${data.name}'s own pages on the date shown, with the sentence it came from. Quotes are verbatim except that long dashes are written as hyphens. "${NOT_STATED}" means the pages read did not say; it does not mean there is no rule.`,
    "",
    "## Contents",
    "",
    "- [Signature](#signature)",
    "- [Delivery](#delivery)",
    "- [Responding and retries](#responding-and-retries)",
    "- [Events](#events)",
    "- [Setup and testing](#setup-and-testing)",
    ...extraSections(data).map((k) => `- [${label(k)}](#${label(k).toLowerCase().replace(/[^a-z0-9 -]/g, "").replace(/ /g, "-")})`),
    ...(data.gotchas?.length ? ["- [Pitfalls the provider warns about](#pitfalls-the-provider-warns-about)"] : []),
    ...(data.conflicts?.length ? ["- [Conflicting or product-specific rules](#conflicting-or-product-specific-rules)"] : []),
    "- [In WebhookVault](#in-webhookvault)",
    "",
    "## Signature",
    "",
  ];
  for (const key of factKeys("signature", data.signature)) lines.push(...renderFact(label(key), data.signature[key]));
  for (const [lang, fact] of Object.entries(data.signature.sdk_helpers ?? {})) lines.push(...renderFact(`Official helper (${label(lang)})`, fact));
  if (data.signature.published_test_vector) lines.push(...renderFact("Published example", data.signature.published_test_vector));
  lines.push("", "## Delivery", "");
  for (const key of factKeys("delivery", data.delivery)) lines.push(...renderFact(label(key), data.delivery[key]));
  lines.push("", "## Responding and retries", "");
  for (const key of factKeys("responding", data.responding)) lines.push(...renderFact(label(key), data.responding[key]));
  lines.push("", "## Events", "", `Full list: ${data.events.full_list_url}`, "");
  for (const [key, v] of Object.entries(data.events)) {
    if (key === "full_list_url" || key === "common") continue;
    if (typeof v === "string") lines.push(`Note: ${clean(v)}`, "");
    else lines.push(...renderFact(label(key), v), "");
  }
  for (const e of data.events.common) lines.push(...renderFact(`\`${clean(e.value)}\``, { ...e, value: clean(e.meaning) }));
  lines.push("", "## Setup and testing", "");
  for (const key of factKeys("setup", data.setup)) lines.push(...renderFact(label(key), data.setup[key]));
  for (const key of extraSections(data)) {
    lines.push("", `## ${label(key)}`, "");
    for (const [k, v] of Object.entries(data[key])) {
      if (Array.isArray(v)) {
        lines.push("", `${label(k)}:`, "");
        v.forEach((f, i) => lines.push(...(f.meaning ? renderFact(`\`${clean(f.value)}\``, { ...f, value: clean(f.meaning) }) : renderFact(`${i + 1}`, f))));
        lines.push("");
      }
      else lines.push(...renderFact(label(k), v));
    }
  }
  if (data.research_notes?.length) {
    lines.push("", "Notes from reading these pages (our words, not the provider's):", "", ...data.research_notes.map((n) => `- ${clean(n)}`));
  }
  if (data.gotchas?.length) {
    lines.push("", "## Pitfalls the provider warns about", "");
    data.gotchas.forEach((g, i) => lines.push(...renderFact(`${i + 1}`, g)));
  }
  if (data.conflicts?.length) {
    lines.push("", "## Conflicting or product-specific rules", "");
    for (const c of data.conflicts) lines.push(`- **${clean(c.topic)}:** ${clean(c.note)}`, ...c.sources.map((s) => `  - Read ${s.read} from ${s.source_url}: "${clean(s.quote)}"`));
  }
  if (data.unreadable?.length) {
    lines.push("", "Pages that could not be read when these facts were taken:", "");
    for (const u of data.unreadable) lines.push(`- ${u.url}: ${clean(u.why)}`);
  }
  lines.push(
    "", "## In WebhookVault", "",
    `What WebhookVault does with ${data.name} requests, read from its provider catalogue on ${presets.read}. These are facts about WebhookVault, not about ${data.name}.`,
    "",
    `- **Signature header it reads:** \`${p.signatureHeader}\``,
    `- **Checks the signature:** ${p.verifies ? `yes (${clean(p.scheme)})` : `no. ${clean(p.scheme)}`}`,
    `- **Secret field label:** ${p.secretLabel}`,
    `- **Where it finds the event name:** ${p.eventLocations.length ? p.eventLocations.map((l) => `${l.kind} \`${l.path}\``).join(", then ") : "nowhere fixed; requests are listed without an event name"}`,
    `- **Where the capture URL goes in ${data.name}:** ${clean(p.setupPath)}`,
    "",
  );
  return lines.join("\n");
}

export function renderQuickFacts({ slug, data }) {
  const rows = QUICK.map(([section, key]) => {
    const fact = data[section]?.[key];
    // "short" is an optional table form of the same value; the full value and its quote stay in facts.md.
    const v = fact ? (fact.short ? clean(fact.short) : show(fact.value) ?? "see references/facts.md") : NOT_STATED;
    return `| ${label(key)} | ${cell(v)} |`;
  });
  return [
    factsStart(slug),
    "| | |",
    "|---|---|",
    ...rows,
    "",
    `Read from ${data.name}'s own pages on ${readRange(data)}. Every value, its source page and the sentence it came from: [references/facts.md](references/facts.md).`,
    FACTS_END,
  ].join("\n");
}

export function replaceQuickFacts(text, block) {
  const start = text.indexOf(FACTS_START_PREFIX);
  const end = text.indexOf(FACTS_END);
  if (start < 0 || end < start) return null;
  return text.slice(0, start) + block + text.slice(end + FACTS_END.length);
}

// ---- the check ------------------------------------------------------------------------------

/** Returns error strings; with write, rewrites generated parts first. Used by validate.mjs too. */
export function runProviderFacts({ write = false } = {}) {
  const errors = [];
  const presetsFile = join(root, "data", "webhookvault-presets.json");
  const presets = JSON.parse(readFileSync(presetsFile, "utf8"));
  if (!/^\d{4}-\d{2}-\d{2}$/.test(presets.read ?? "")) errors.push("data/webhookvault-presets.json: read must be a YYYY-MM-DD date");
  const providers = loadProviders();
  const seen = new Set();
  for (const prov of providers) {
    seen.add(prov.slug);
    const where = relative(root, prov.file).replace(/\\/g, "/");
    const errs = checkProvider(prov, presets);
    errors.push(...errs.map((e) => `${where}: ${e}`));
    if (errs.length) continue;
    const skillDir = join(root, "skills", `${prov.slug}-webhooks`);
    const skillFile = join(skillDir, "SKILL.md");
    if (!existsSync(skillFile)) { errors.push(`${where}: no skill folder skills/${prov.slug}-webhooks`); continue; }
    const factsFile = join(skillDir, "references", "facts.md");
    const wantFacts = renderFactsMd(prov, presets);
    const haveFacts = existsSync(factsFile) ? readFileSync(factsFile, "utf8").replace(/\r\n/g, "\n") : null;
    const skillText = readFileSync(skillFile, "utf8").replace(/\r\n/g, "\n");
    const wantSkill = replaceQuickFacts(skillText, renderQuickFacts(prov));
    if (wantSkill === null) { errors.push(`skills/${prov.slug}-webhooks/SKILL.md: no facts block (${FACTS_START_PREFIX} ... ${FACTS_END})`); continue; }
    if (write) {
      if (haveFacts !== wantFacts) { mkdirSync(dirname(factsFile), { recursive: true }); writeFileSync(factsFile, wantFacts); console.log(`wrote skills/${prov.slug}-webhooks/references/facts.md`); }
      if (wantSkill !== skillText) { writeFileSync(skillFile, wantSkill); console.log(`stamped skills/${prov.slug}-webhooks/SKILL.md`); }
    } else {
      if (haveFacts !== wantFacts) errors.push(`skills/${prov.slug}-webhooks/references/facts.md is out of date (run node tools/provider-facts.mjs --write)`);
      if (wantSkill !== skillText) errors.push(`skills/${prov.slug}-webhooks/SKILL.md facts block is out of date (run node tools/provider-facts.mjs --write)`);
    }
  }
  const skills = existsSync(join(root, "skills")) ? readdirSync(join(root, "skills")) : [];
  for (const s of skills) {
    const m = s.match(/^(.+)-webhooks$/);
    if (m && !seen.has(m[1])) errors.push(`skills/${s}: a provider skill with no data/providers/${m[1]}.json`);
  }
  return errors;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const errors = runProviderFacts({ write: process.argv.includes("--write") });
  for (const e of errors) console.log(`error    ${e}`);
  console.log(`provider facts: ${errors.length} error(s).`);
  process.exit(errors.length ? 1 : 0);
}
