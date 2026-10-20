#!/usr/bin/env node
// Checks every skill in skills/ against the repository's rules and exits non-zero on any error.
//
//   node tools/validate.mjs            check everything
//   node tools/validate.mjs --stamp    first write shared/safety-block.md into every workflow skill
//
// No dependencies: plain Node 20 or later. Rules come from the Agent Skills specification
// (agentskills.io), the claude.ai upload limits, and this repository's own voice and safety rules
// (CONTRIBUTING.md). Every rule here has a reason in CONTRIBUTING.md; change both together.

import { readFileSync, writeFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, dirname, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { runProviderFacts } from "./provider-facts.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const skillsDir = join(root, "skills");
const stamp = process.argv.includes("--stamp");

const errors = [];
const warnings = [];
const fail = (file, message) => errors.push(`${relative(root, file)}: ${message}`);
const warn = (file, message) => warnings.push(`${relative(root, file)}: ${message}`);

// ---- limits -------------------------------------------------------------------------------

const MAX_DESCRIPTION = 200; // claude.ai upload limit (the spec allows 1024)
const MAX_SKILL_LINES = 400; // the spec recommends under 500; this repo keeps headroom
const MAX_NAME = 64;
const MAX_COMPATIBILITY = 500;
const ALLOWED_KEYS = new Set(["name", "description", "license", "compatibility", "metadata"]);
const REQUIRED_METADATA = ["author", "version", "repository"];
const REPOSITORY = "https://github.com/WebhookVault/skills";
const WORKFLOW_PREFIX = "webhookvault-";
const SAFETY_START = "<!-- safety:start (stamped from shared/safety-block.md; edit there) -->";
const SAFETY_END = "<!-- safety:end -->";

// ---- voice and safety rules ----------------------------------------------------------------

const textRules = [
  { re: /[–—]/u, why: "en or em dash; use a colon, comma, full stop or parentheses", inCode: true },
  { re: /\p{Extended_Pictographic}/u, why: "emoji", inCode: true },
  // Invisible or line-breaking characters typed raw: unreadable in review, and U+2028 ends a line
  // inside a JavaScript regex or a C# string. Write them as \u escapes.
  { re: /[\u200b-\u200f\u2028\u2029\u202a-\u202e\u2066-\u2069\ufeff]/u, why: "an invisible or line-separator character; write it as a \\u escape", inCode: true },
  { re: /\bthe vault\b/i, why: 'say "WebhookVault", never "the vault"' },
  { re: /\bwatchdogs?\b[^.\n]{0,60}\blearn(s|ed|ing)?\b/i, why: "watchdogs do not learn; the owner sets the interval" },
  { re: /\b(as a|being|i am a|we are) human\b|\bhuman[- ]written\b|\breal humans?\b/i, why: "no assertions about humans" },
  { re: /\b(tunnel(s|ing)?|ngrok|smee)\b/i, why: "no tunnels or relays: WebhookVault never delivers to localhost" },
  { re: /\b(forward|relay|deliver)(s|ed|ing)? (it |them |requests |webhooks )?to (your )?localhost\b/i, why: "never imply delivery to localhost" },
  { re: /\b(hookdeck|webhook\.site|webhookrelay|webhook relay)\b/i, why: "no other webhook product is named in this repository" },
];

const secretRules = [
  { re: /\bwv_live_[A-Za-z0-9]{12,}/, why: "a WebhookVault key" },
  { re: /\bwhsec_[A-Za-z0-9+/=]{20,}/, why: "a signing secret" },
  { re: /\b[sr]k_live_[A-Za-z0-9]{10,}/, why: "a live provider key" },
  { re: /\bxox[abpr]-[A-Za-z0-9-]{10,}/, why: "a Slack token" },
  { re: /-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----/, why: "a private key" },
];

// Test values are allowed when the line says so, as samples and test vectors must.
const marksTestValue = (line) => /\b(test|example|fixture|dummy|placeholder|not a real)\b/i.test(line);

// CONTRIBUTING.md and AGENTS.md state the voice rules, so they name what the rules forbid; only the
// rules that apply everywhere (dashes, emoji) are checked in them.
const RULE_DOCS = new Set(["CONTRIBUTING.md", "AGENTS.md"]);

function checkText(file, text) {
  const lines = text.split("\n");
  const ruleDoc = RULE_DOCS.has(relative(root, file));
  let inFence = false;
  lines.forEach((line, i) => {
    if (/^\s*```/.test(line)) inFence = !inFence;
    for (const rule of textRules) {
      // Code may quote a header or a variable; prose rules apply outside code fences, the rules
      // marked inCode everywhere.
      if ((inFence || ruleDoc) && !rule.inCode) continue;
      if (rule.re.test(line)) fail(file, `line ${i + 1}: ${rule.why}`);
    }
    for (const rule of secretRules) {
      if (rule.re.test(line) && !marksTestValue(line)) fail(file, `line ${i + 1}: looks like ${rule.why}; use a marked test value`);
    }
  });
}

// ---- frontmatter --------------------------------------------------------------------------

// The repository's frontmatter is a strict subset of YAML: top-level "key: value" lines and one
// "metadata:" map of two-space-indented "key: value" lines. Anything else is an error, so a file
// that some other YAML reader would take differently never ships.
function parseFrontmatter(file, text) {
  if (!text.startsWith("---\n")) return fail(file, "SKILL.md must start with a --- frontmatter line"), null;
  const end = text.indexOf("\n---\n", 4);
  if (end < 0) return fail(file, "frontmatter is not closed with ---"), null;
  const block = text.slice(4, end).split("\n");
  const data = {};
  let inMetadata = false;
  for (const raw of block) {
    if (raw.trim() === "") continue;
    const nested = raw.startsWith("  ");
    const m = raw.trim().match(/^([a-z][a-z0-9-]*):(?: (.*))?$/);
    if (!m) { fail(file, `frontmatter line not understood: ${raw}`); continue; }
    const [, key, value = ""] = m;
    if (nested) {
      if (!inMetadata) { fail(file, `indented line outside metadata: ${raw}`); continue; }
      if (!/^".*"$/.test(value)) fail(file, `metadata.${key} must be a quoted string (the spec allows strings only)`);
      data.metadata[key] = unquote(value);
      continue;
    }
    inMetadata = false;
    if (!ALLOWED_KEYS.has(key)) { fail(file, `frontmatter key "${key}" is not in the Agent Skills spec set used here`); continue; }
    if (key === "metadata") {
      if (value !== "") fail(file, "metadata must be a map on the following lines");
      data.metadata = {};
      inMetadata = true;
      continue;
    }
    data[key] = unquote(value);
  }
  return { data, bodyStart: end + 5 };
}

function unquote(value) {
  const v = value.trim();
  if (/^".*"$/.test(v)) return v.slice(1, -1).replace(/\\"/g, '"');
  if (/^'.*'$/.test(v)) return v.slice(1, -1).replace(/''/g, "'");
  return v;
}

// ---- links --------------------------------------------------------------------------------

function checkLinks(file, text, skillRoot) {
  const links = [...text.matchAll(/\]\(([^)\s]+)\)/g)].map((m) => m[1]);
  for (const link of links) {
    if (/^(https?:|mailto:|#)/.test(link)) {
      if (/^https?:\/\/github\.com\/webhookvault\/skills/i.test(link) && !link.startsWith(REPOSITORY)) {
        fail(file, `link to this repository must use ${REPOSITORY}: ${link}`);
      }
      continue;
    }
    const target = resolve(dirname(file), link.split("#")[0]);
    if (!target.startsWith(skillRoot + sep) && target !== skillRoot) {
      fail(file, `link leaves the skill folder (a skill must install alone; link other skills by URL): ${link}`);
      continue;
    }
    if (!existsSync(target)) fail(file, `link target does not exist: ${link}`);
    const depth = relative(skillRoot, target).split(sep).length;
    if (depth > 2) fail(file, `link is more than one folder deep from SKILL.md: ${link}`);
  }
}

// ---- safety block -------------------------------------------------------------------------

const safetyBlock = readFileSync(join(root, "shared", "safety-block.md"), "utf8").replace(/\r\n/g, "\n").trimEnd();

function checkSafety(file, text) {
  const start = text.indexOf(SAFETY_START);
  const end = text.indexOf(SAFETY_END);
  if (start < 0 || end < start) return fail(file, `workflow skill is missing the stamped safety block (run node tools/validate.mjs --stamp)`), text;
  const current = text.slice(start + SAFETY_START.length, end).trim();
  if (current === safetyBlock) return text;
  if (stamp) return text.slice(0, start + SAFETY_START.length) + "\n" + safetyBlock + "\n" + text.slice(end);
  fail(file, "the safety block differs from shared/safety-block.md (run node tools/validate.mjs --stamp)");
  return text;
}

// ---- marketplace --------------------------------------------------------------------------

function checkMarketplace(skillNames) {
  const file = join(root, ".claude-plugin", "marketplace.json");
  if (!existsSync(file)) return fail(file, "missing");
  let market;
  try { market = JSON.parse(readFileSync(file, "utf8")); } catch (e) { return fail(file, `not valid JSON: ${e.message}`); }
  for (const key of ["name", "owner", "plugins"]) if (!market[key]) fail(file, `missing required "${key}"`);
  const listed = new Map();
  for (const plugin of market.plugins ?? []) {
    if (!/^[a-z0-9][a-z0-9-]*$/.test(plugin.name ?? "")) fail(file, `plugin name "${plugin.name}" must be lowercase letters, digits and hyphens`);
    if (/^(claude|anthropic|anthropics|cc-plugin)-/.test(plugin.name ?? "")) fail(file, `plugin name "${plugin.name}" uses a reserved prefix`);
    if (plugin.source !== "./") fail(file, `plugin "${plugin.name}" must use source "./" (skills live in the root skills/ folder)`);
    for (const path of plugin.skills ?? []) {
      const m = path.match(/^\.\/skills\/([a-z0-9-]+)$/);
      if (!m) { fail(file, `plugin "${plugin.name}" lists "${path}"; expected ./skills/<name>`); continue; }
      if (!skillNames.has(m[1])) fail(file, `plugin "${plugin.name}" lists ${m[1]}, which is not a skill folder`);
      if (listed.has(m[1])) fail(file, `${m[1]} is listed by both ${listed.get(m[1])} and ${plugin.name}`);
      listed.set(m[1], plugin.name);
    }
  }
  for (const name of skillNames) if (!listed.has(name)) fail(file, `skill ${name} is in no plugin`);
}

// ---- the walk -----------------------------------------------------------------------------

function walk(dir, visit) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (entry === "node_modules" || entry === ".git" || entry === "bin" || entry === "obj" || entry === "__pycache__" || entry === ".venv") continue;
      walk(full, visit);
    } else {
      visit(full);
    }
  }
}

const skillNames = new Set(existsSync(skillsDir) ? readdirSync(skillsDir).filter((d) => statSync(join(skillsDir, d)).isDirectory()) : []);

for (const name of [...skillNames].sort()) {
  const skillRoot = join(skillsDir, name);
  const file = join(skillRoot, "SKILL.md");
  if (!existsSync(file)) { fail(skillRoot, "no SKILL.md"); continue; }
  let text = readFileSync(file, "utf8").replace(/\r\n/g, "\n");

  if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(name) || name.length > MAX_NAME) fail(skillRoot, "folder name must be lowercase letters and digits joined by single hyphens, at most 64");
  if (/(^|-)(claude|anthropic)(-|$)/.test(name)) fail(skillRoot, 'names never contain "claude" or "anthropic"');

  const parsed = parseFrontmatter(file, text);
  if (parsed) {
    const { data } = parsed;
    if (data.name !== name) fail(file, `name "${data.name}" must equal the folder name "${name}"`);
    if (!data.description) fail(file, "description is required");
    else {
      if (data.description.length > MAX_DESCRIPTION) fail(file, `description is ${data.description.length} characters; at most ${MAX_DESCRIPTION}`);
      if (!/\bUse when\b/.test(data.description)) fail(file, 'description must say when to use the skill ("Use when ...")');
      if (/\b(I|you|we)\b/.test(data.description)) fail(file, "description is written in the third person");
    }
    if (data.license !== "MIT") fail(file, "license must be MIT");
    if (data.compatibility && data.compatibility.length > MAX_COMPATIBILITY) fail(file, "compatibility is over 500 characters");
    if (name.startsWith(WORKFLOW_PREFIX) && !data.compatibility) fail(file, "workflow skills state their compatibility (the MCP server or the API)");
    for (const key of REQUIRED_METADATA) if (!data.metadata?.[key]) fail(file, `metadata.${key} is required`);
    if (data.metadata?.repository && data.metadata.repository !== REPOSITORY) fail(file, `metadata.repository must be ${REPOSITORY}`);
    if (data.metadata?.version && !/^\d+\.\d+\.\d+$/.test(data.metadata.version)) fail(file, "metadata.version is x.y.z");
  }

  const lineCount = text.split("\n").length;
  if (lineCount > MAX_SKILL_LINES) fail(file, `${lineCount} lines; at most ${MAX_SKILL_LINES} (move detail to references/)`);

  // The safety block belongs in every skill that drives the MCP server (it reads captured content
  // and can change things); an API-only skill such as CI testing carries its own key rules.
  if (name.startsWith(WORKFLOW_PREFIX) && parsed?.data.metadata?.["mcp-tools"]) {
    const stamped = checkSafety(file, text);
    if (stamped !== text) { writeFileSync(file, stamped); text = stamped; console.log(`stamped ${relative(root, file)}`); }
  }

  walk(skillRoot, (f) => {
    if (!/\.(md|txt|json|ya?ml|js|mjs|ts|py|cs|csproj|sh|toml|go|php)$/.test(f)) return;
    const content = readFileSync(f, "utf8").replace(/\r\n/g, "\n");
    checkText(f, content);
    if (f.endsWith(".md")) {
      checkLinks(f, content, skillRoot);
      if (f !== file && content.split("\n").length > 100 && !/^## Contents/m.test(content)) {
        fail(f, "a reference over 100 lines starts with a ## Contents list");
      }
    }
  });
}

// Repository files outside skills/ follow the same voice rules.
for (const f of ["README.md", "CONTRIBUTING.md", "AGENTS.md", "SECURITY.md", "CHANGELOG.md", join("shared", "safety-block.md")]) {
  const full = join(root, f);
  if (existsSync(full)) checkText(full, readFileSync(full, "utf8").replace(/\r\n/g, "\n"));
  else fail(full, "missing");
}

checkMarketplace(skillNames);

// Provider skills: every fact well formed and sourced, and the generated parts current.
for (const e of runProviderFacts()) errors.push(e);

for (const w of warnings) console.log(`warning  ${w}`);
for (const e of errors) console.log(`error    ${e}`);
console.log(`${skillNames.size} skills checked: ${errors.length} error(s), ${warnings.length} warning(s).`);
process.exit(errors.length ? 1 : 0);
