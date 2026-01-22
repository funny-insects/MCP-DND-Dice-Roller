
# MCP D&D Dice Roller

Python MCP server providing auditable D&D dice rolls (see [SPEC.md](SPEC.md)).

## Install

Using `uv`:

```bash
uv sync
```

Using `pip`:

```bash
python -m pip install -e .
```

## Run (stdio)

Run directly:

```bash
python main.py
```

Or via the console script:

```bash
mcp-dnd-dice-roller
```

## Dev / Inspector

If you installed `mcp[cli]`, you can use the MCP CLI tooling (exact commands may vary by MCP version):

```bash
mcp dev main.py
```

## Tests

Using `uv`:

```bash
uv sync --extra dev
uv run python -m pytest
```

### Generate Task 2 proof artifacts

This repo includes a script that generates the exact text artifacts used as proof for Parent Task 2:

```bash
bash scripts/make_task2_artifacts.sh
```

Outputs:
- `artifacts/pytest_task2.txt`
- `artifacts/manual_task2.txt`
- `artifacts/rejections_task2.txt`

## Tool

Tool name: `roll_dice`

Examples of valid requests:
- `d20`
- `roll a d20 with advantage +3 modifier`
- `2d10 + 2d4 + 4`

Examples of invalid requests (hard error, no roll performed):
- `2d7 + 1` (unsupported die)
- `d20 with advantage + d20` (invalid advantage usage)

