#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p artifacts

# Ensure dev deps (pytest) are installed into the uv-managed venv.
uv sync --extra dev

# 1) Unit tests
uv run python -m pytest -q | tee artifacts/pytest_task2.txt

# 2) Manual acceptance examples
uv run python - <<'PY' | tee artifacts/manual_task2.txt
from mcp_dnd_dice_roller.parser import parse_request
from mcp_dnd_dice_roller.dice import roll_from_text

examples = [
  "d20",
  "2d10 + 2d4 + 4",
  "roll a d20 with advantage and a +3 modifier",
]

for e in examples:
  p = parse_request(e)
  print("INPUT:", e)
  print("NORMALIZED_EXPR:", p.normalized_expression)
  r = roll_from_text(e)
  print("TOTAL:", r["total"])
  print("EXPLANATION:", r["explanation"])
  print("-"*40)
PY

# 3) Rejections (validation proof)
uv run python - <<'PY' | tee artifacts/rejections_task2.txt
from mcp_dnd_dice_roller.parser import parse_request
from mcp_dnd_dice_roller.errors import DiceError

bad = ["2d7 + 1", "advantage", "2d20 with advantage", "(2d6 + 3) * 2"]
for e in bad:
  try:
    parse_request(e)
    print(e, "->", "UNEXPECTED_SUCCESS")
  except DiceError as ex:
    print(e, "->", str(ex))
PY

echo "Wrote artifacts/*.txt"
