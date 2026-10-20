#!/usr/bin/env bash
# Runs every example's tests once and exits non-zero if any fail. The maintainer runs this before a
# merge or a tag (there is no CI on this repository).
#
#   bash tools/test-examples.sh                 every skill
#   bash tools/test-examples.sh <skill> ...     only these skills
#
# Needs Node.js 18+, Python 3.9+ and the .NET 10 SDK. Python examples get their own virtual
# environment (examples/python/.venv, ignored by git) with the pinned requirements.
set -uo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

if [ "$#" -gt 0 ]; then skills=("$@"); else skills=(); for d in skills/*/; do skills+=("$(basename "$d")"); done; fi

failed=0
ran=0
for skill in "${skills[@]}"; do
  # Scripts that ship with a skill carry their tests beside them (standard library only).
  scripts="skills/$skill/scripts"
  if ls "$scripts"/test_*.py > /dev/null 2>&1; then
    echo "== $scripts"; ran=$((ran + 1))
    (cd "$scripts" && python -m unittest discover -p "test_*.py") || failed=$((failed + 1))
  fi

  examples="skills/$skill/examples"
  [ -d "$examples" ] || continue

  for dir in "$examples"/node "$examples"/*/node; do
    [ -f "$dir/package.json" ] || continue
    echo "== $dir"; ran=$((ran + 1))
    (cd "$dir" && { [ ! -f package-lock.json ] || npm ci --silent; } && node --test) || failed=$((failed + 1))
  done

  for dir in "$examples"/python "$examples"/*/python; do
    [ -d "$dir" ] || continue
    ls "$dir"/test_*.py > /dev/null 2>&1 || continue
    echo "== $dir"; ran=$((ran + 1))
    (
      cd "$dir" || exit 1
      if [ ! -d .venv ]; then python -m venv .venv || exit 1; fi
      py=.venv/bin/python; [ -x "$py" ] || py=.venv/Scripts/python
      if [ -f requirements.txt ]; then "$py" -m pip install -q -r requirements.txt || exit 1; fi
      "$py" -m unittest discover -p "test_*.py"
    ) || failed=$((failed + 1))
  done

  for dir in "$examples"/csharp "$examples"/*/csharp; do
    [ -d "$dir" ] || continue
    ls "$dir"/*.csproj > /dev/null 2>&1 || continue
    echo "== $dir"; ran=$((ran + 1))
    (cd "$dir" && dotnet test -nologo -v q) || failed=$((failed + 1))
  done
done

echo "$ran example suite(s) run, $failed failed."
[ "$failed" -eq 0 ]
