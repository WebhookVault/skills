#!/usr/bin/env node
// Checks the WebhookVault workflow skills against the MCP server's published contract
// (data/mcp-tools.snapshot.json, a copy of https://docs.webhookvault.net/mcp-tools.json).
//
//   node tools/check-tools.mjs
//
// Fails when a skill names a tool the server does not serve, passes an argument a tool does not
// take, lists tools in metadata that its text does not use (or the reverse), was last reviewed
// against an older contract, or drifts from the MCP prompts' safety lines; and when the server
// serves a tool no skill covers and data/unused-tools.txt does not list it.

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const errors = [];
const fail = (file, message) => errors.push(`${relative(root, file)}: ${message}`);

const snapshot = JSON.parse(readFileSync(join(root, "data", "mcp-tools.snapshot.json"), "utf8"));
const meta = JSON.parse(readFileSync(join(root, "data", "mcp-tools.snapshot.meta.json"), "utf8"));
const tools = new Map(snapshot.tools.map((t) => [t.name, new Set(Object.keys(t.inputSchema?.properties ?? {}))]));
const prompts = new Map(snapshot.prompts.map((p) => [p.name, snapshot.promptTexts?.texts?.[p.name] ?? ""]));

const lines = (file) => (existsSync(file) ? readFileSync(file, "utf8").split(/\r?\n/).map((l) => l.trim()).filter((l) => l && !l.startsWith("#")) : []);
const nonToolWords = new Set(lines(join(root, "data", "non-tool-words.txt")));
const unusedTools = new Set(lines(join(root, "data", "unused-tools.txt")));
const parity = JSON.parse(readFileSync(join(root, "data", "prompt-parity.json"), "utf8"));

function filesOf(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) out.push(...filesOf(full));
    else if (full.endsWith(".md")) out.push(full);
  }
  return out;
}

function metadataOf(text) {
  const front = text.match(/^---\n([\s\S]*?)\n---\n/);
  const get = (key) => front?.[1].match(new RegExp(`^  ${key}: "([^"]*)"$`, "m"))?.[1];
  return { tools: get("mcp-tools"), contract: get("mcp-contract") };
}

const mentionedAnywhere = new Set();
const skillsDir = join(root, "skills");

for (const name of readdirSync(skillsDir).sort()) {
  if (!name.startsWith("webhookvault-")) continue;
  const skillRoot = join(skillsDir, name);
  const skillFile = join(skillRoot, "SKILL.md");
  const skillText = readFileSync(skillFile, "utf8").replace(/\r\n/g, "\n");
  const { tools: listed, contract } = metadataOf(skillText);
  const used = new Set();

  for (const file of filesOf(skillRoot)) {
    const text = readFileSync(file, "utf8").replace(/\r\n/g, "\n");
    // A tool call written as `tool_name(argA, argB=value)`: the tool and every argument are checked.
    for (const m of text.matchAll(/`([a-z][a-z0-9_]*)\(([^)`]*)\)`/g)) {
      const [, tool, args] = m;
      if (!tools.has(tool)) { fail(file, `\`${tool}(...)\` is not a tool the server serves`); continue; }
      used.add(tool);
      for (const arg of args.split(",").map((a) => a.split("=")[0].trim()).filter(Boolean)) {
        if (!tools.get(tool).has(arg)) fail(file, `\`${tool}\` takes no argument "${arg}" (it takes: ${[...tools.get(tool)].join(", ") || "none"})`);
      }
    }
    // Any other snake_case word in backticks is a tool or a listed non-tool word (an error code,
    // a field name).
    // (A single word such as `whoami` counts when it is a tool; an unknown one is only flagged when
    // it has an underscore, since plain words in backticks are common.)
    for (const m of text.matchAll(/`([a-z][a-z0-9_]*)`/g)) {
      const word = m[1];
      if (tools.has(word)) used.add(word);
      else if (word.includes("_") && !word.includes("__") && !nonToolWords.has(word)) {
        fail(file, `\`${word}\` is neither a tool in the snapshot nor in data/non-tool-words.txt`);
      }
    }
  }

  const listedSet = new Set((listed ?? "").split(/\s+/).filter(Boolean));
  const apiSkill = /compatibility: .*WebhookVault API/.test(skillText) && listedSet.size === 0;
  if (!listed && !apiSkill && used.size) fail(skillFile, "metadata.mcp-tools is missing");
  for (const t of listedSet) if (!tools.has(t)) fail(skillFile, `metadata.mcp-tools names ${t}, which the server does not serve`);
  for (const t of used) if (!listedSet.has(t)) fail(skillFile, `uses ${t} but metadata.mcp-tools does not list it`);
  for (const t of listedSet) if (!used.has(t)) fail(skillFile, `metadata.mcp-tools lists ${t} but the skill never uses it`);
  if (used.size && (!contract || contract < meta.copiedOn)) {
    fail(skillFile, `metadata.mcp-contract is ${contract ?? "missing"}; the snapshot is from ${meta.copiedOn}. Re-read the skill against it, then update the date.`);
  }
  for (const t of used) mentionedAnywhere.add(t);
}

for (const tool of tools.keys()) {
  if (!mentionedAnywhere.has(tool) && !unusedTools.has(tool)) {
    fail(join(root, "data", "unused-tools.txt"), `the server serves ${tool} but no skill uses it; write it into a skill or list it here with a reason`);
  }
}
for (const tool of unusedTools) {
  if (!tools.has(tool)) fail(join(root, "data", "unused-tools.txt"), `${tool} is not served any more; remove it`);
  else if (mentionedAnywhere.has(tool)) fail(join(root, "data", "unused-tools.txt"), `${tool} is used by a skill now; remove it from this list`);
}

// The MCP prompts and the skills that carry the same flow keep the same safety lines
// (decision 2026-10-20 03:15, S5).
for (const [prompt, rule] of Object.entries(parity)) {
  const text = prompts.get(prompt);
  if (text === undefined) { fail(join(root, "data", "prompt-parity.json"), `the server has no prompt ${prompt}`); continue; }
  const skillRoot = join(skillsDir, rule.skill);
  // Whitespace collapsed on both sides, so a phrase wrapped across lines still matches.
  const flat = (s) => s.replace(/\s+/g, " ");
  const skillText = existsSync(skillRoot) ? flat(filesOf(skillRoot).map((f) => readFileSync(f, "utf8")).join("\n")) : "";
  if (!skillText) { fail(join(root, "data", "prompt-parity.json"), `skill ${rule.skill} does not exist`); continue; }
  for (const pattern of rule.both) {
    const re = new RegExp(pattern, "i");
    if (!re.test(flat(text))) fail(join(root, "data", "prompt-parity.json"), `the ${prompt} prompt no longer says /${pattern}/`);
    if (!re.test(skillText)) fail(skillRoot, `the skill no longer says /${pattern}/, which the ${prompt} prompt says`);
  }
}

for (const e of errors) console.log(`error    ${e}`);
console.log(`Checked against the snapshot of ${meta.copiedOn} (${tools.size} tools, ${prompts.size} prompts): ${errors.length} error(s).`);
process.exit(errors.length ? 1 : 0);
