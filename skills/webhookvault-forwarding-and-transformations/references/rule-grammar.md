# Transformation rule grammar

## Contents

- The document
- Paths
- Conditions
- Steps
- compute
- Absent values
- Bounds

Read from https://docs.webhookvault.net/documentation/transformations on 2026-10-20. The complete
specification for models is at https://app.webhookvault.net/llms-transformations.txt; prefer it when
it disagrees with this summary.

## The document

```json
{
  "version": 1,
  "name": "invoices only, flattened",
  "when": { "all": [ { "path": "body.type", "op": "startsWith", "value": "invoice." } ] },
  "steps": [
    { "op": "keep", "paths": ["body.id", "body.type", "body.data.object"] },
    { "op": "rename", "from": "body.data.object.id", "to": "body.invoiceId" },
    { "op": "set", "path": "headers.X-Relayed-By", "value": "webhookvault" }
  ]
}
```

## Paths

| Root | Addresses | Writable |
|---|---|---|
| `body` | The body parsed as JSON: `body.data.object.id`, `body.items[0].sku`, `body.items[*].sku` | Yes |
| `headers` | Request headers, one level, case-insensitive: `headers.X-Event` | Yes |
| `query` | Query-string parameters: `query.ref` | Yes |
| `path` | The request path as a string | No (conditions and templates only) |

## Conditions

`when` is `all`, `any` or `not` over predicates `{ "path", "op", "value" }`. Ops: `equals`,
`notEquals`, `startsWith`, `endsWith`, `contains`, `exists`, `gt`, `gte`, `lt`, `lte`, `matches`
(a regular expression on a linear-time engine: no backreferences or lookarounds). Without `when`
the rule applies to every delivery. A rule that does not match delivers the request unchanged.

## Steps

| Op | Fields | Effect |
|---|---|---|
| `keep` | `paths` | Keep only these paths inside their root |
| `remove` | `paths` | Delete these paths (`headers` alone empties all headers) |
| `rename` or `move` | `from`, `to` | Move a value, across roots if wanted |
| `set` | `path`, `value` | Write any JSON value, creating containers |
| `default` | `path`, `value` | Like set, only when the path is absent |
| `redact` | `paths`, `with` | Replace values with a fixed string (default `***`) |
| `template` | `path`, `template` | Write a string from `{{path}}` placeholders |
| `parseJson` | `path` | Turn a JSON-text string field into the parsed value |
| `toString` | `path` | Turn a value into its JSON text |
| `compute` | `path`, `fn`, `args` | Write a value computed from the payload |

Any step may carry `"enabled": false`. Steps run in order and see earlier results. A step that
cannot apply (a missing path) is a no-op with a note; the delivery still goes out.

## compute

`fn` names one function; `args` entries are a path (`body.amount_cents`), a literal JSON value, or
a nested call `{"fn": "...", "args": [...]}`. Write `{"literal": "body.x"}` for text that looks
like a path. No operators, variables or loops.

| Group | Functions |
|---|---|
| Text | `lower` `upper` `trim` `slice` `replace` `split` `concat` `padStart` |
| Numbers | `add` `sub` `mul` `div` `round` `abs` `min` `max` |
| Collections | `sum` `count` `avg` `first` `last` `join` |
| Time | `now` `unixToIso` `isoToUnix` |
| Encoding | `base64` `base64Decode` `sha256Hex` |
| Absence | `coalesce` `ifEmpty` |

Collection functions read a path with `[*]`: `sum` over `body.items[*].amount`.

## Absent values

A missing path is absent, and absent is not zero: arithmetic on it is absent, `count` of it is
absent, `concat` with any absent argument is absent. A type mismatch or division by zero is absent
with a note. When a call is absent the target path is left as it was. `"12.5"` reads as a number;
`"1,234"` does not. Use `coalesce` for a default:
`{ "op": "compute", "path": "body.currency", "fn": "coalesce", "args": ["body.currency", { "literal": "USD" }] }`.

## Bounds

64 steps and 32 KB per document, 64 paths per step, 8 KB string values, 200-character patterns;
compute: 4 levels of nesting, 8 arguments per call, 16 calls per step; at run time 1000 elements
from one path, 5000 per step, 8 KB results. Up to 20 rules per action.
