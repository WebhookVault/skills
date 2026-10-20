# Examples: escaping tested against the documented rules

Escaping for Slack, Telegram (MarkdownV2 and HTML), HTML and logs, and a Discord message builder that
suppresses mentions and link previews, in three languages with no dependencies beyond the test
framework.

| Folder | Run the tests |
|---|---|
| `node/` | `node --test` (Node.js 18 or later) |
| `python/` | `python -m unittest test_escape.py` (Python 3.9 or later) |
| `csharp/` | `dotnet test` (.NET 10 SDK) |

`fixtures/cases.json` holds every input and its expected output, written by hand from each
destination's documented rules (sources and the read date are in the file). All three languages must
produce exactly those outputs, so the test oracle is the documentation, not any one implementation.

The Discord builder is checked for `allowed_mentions: {"parse": []}`, the `SUPPRESS_EMBEDS` flag and
the 2000-character content limit. Mention text is kept as written; only its effect is suppressed.
