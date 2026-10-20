"""Turns a captured webhook body into a fixture safe to commit: email addresses, phone numbers and long
digit runs inside JSON string values are replaced with obvious test values; keys, structure, numbers
and every other value are kept. Standard library only.

    python scrub_fixture.py captured.json > tests/fixtures/order-created.json

Re-serialises the JSON (two-space indent, keys in their original order). A signature over the original
bytes will not match the scrubbed body: sign the fixture with a test secret in the test instead.
Read the output before committing it: names, addresses and free text are not detected.
"""

import json
import re
import sys

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# A phone number: an optional +, then 7 to 15 digits with optional spaces, dots, dashes or brackets.
PHONE = re.compile(r"\+?\(?\d[\d\s().-]{5,}\d")
# Dates and version-like runs look like phone numbers to the pattern above and are kept.
NOT_A_PHONE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,3}(\.\d{1,3}){2,}")
LONG_DIGITS = re.compile(r"\d{12,}")


def _phone(match) -> str:
    text = match.group()
    # A bare run of 12 or more digits is the long-digit rule's (card and account numbers), not a phone.
    if LONG_DIGITS.fullmatch(text) or NOT_A_PHONE.fullmatch(text.strip()) or sum(c.isdigit() for c in text) < 7:
        return text
    return "+15550100"


def scrub_string(value: str) -> str:
    value = EMAIL.sub("person@example.test", value)
    value = LONG_DIGITS.sub(lambda m: "0" * len(m.group()), value)
    return PHONE.sub(_phone, value)


def scrub(node):
    if isinstance(node, dict):
        return {k: scrub(v) for k, v in node.items()}
    if isinstance(node, list):
        return [scrub(v) for v in node]
    if isinstance(node, str):
        return scrub_string(node)
    return node


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    json.dump(scrub(data), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
