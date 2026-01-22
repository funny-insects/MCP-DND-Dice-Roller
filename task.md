# Implementation Tasks — MCP D&D Dice Roller (Python)

This task file breaks down the implementation into **demoable, testable parent tasks** derived from [SPEC.md](SPEC.md). Each parent task delivers working functionality with clear proof artifacts.

---

## Parent Task 1 — Project Skeleton + MCP Tool Wiring

### Purpose
Create a runnable Python MCP server that exposes the `roll_dice` tool endpoint and can be invoked from Claude Code (even before full parsing/rolling is implemented).

### Functional requirements satisfied
- Spec §5.1: expose one tool `roll_dice`
- Spec §5.2: tool input schema accepts `text: str`
- Spec §9.1: MCP server skeleton demoable

### Proof artifacts
- A developer can run the server locally and invoke `roll_dice`.
- A smoke test (or manual CLI invocation) returns a valid JSON object (stubbed) without crashing.
- Basic “hello” response includes required top-level keys (even if placeholder): `request_id`, `timestamp`, `input`.

### Relevant files
Create/modify:
- `pyproject.toml` (or `requirements.txt`) — dependencies
- `src/mcp_dnd_dice_roller/__init__.py`
- `src/mcp_dnd_dice_roller/server.py` — MCP server entry
- `README.md` — how to run and configure with Claude Code
- `tests/test_smoke.py` — optional smoke test

### Sub-tasks
1. Choose packaging layout (`src/` layout recommended) and add minimal Python project config.
2. Add MCP SDK dependency and implement `server.py` with a `roll_dice(text)` tool handler.
3. Return a stubbed but schema-shaped response to validate end-to-end wiring.
4. Add run instructions to `README.md` (local run + Claude Code MCP config snippet).
5. Add a smoke test that calls the tool handler function directly.

---

## Parent Task 2 — Parser + Normalizer (v1 Grammar)

### Purpose
Implement deterministic parsing from natural language to a normalized internal representation that supports dice terms and +/− constants, while rejecting out-of-scope syntax.

### Functional requirements satisfied
- Spec §4.2: supported expression grammar (dice terms + integer constants; +/− only)
- Spec §6.2: parser strategy (normalization, detection, extraction)
- Spec §8.1 (Parsing tests): accept/reject examples

### Proof artifacts
- Unit tests cover at least the accepted examples:
  - `d20`, `d100`, `2d10 + 2d4 + 4`, “roll a d20 with advantage and a +3 modifier”
- Unit tests cover at least the rejected examples:
  - `2d7 + 1`, `advantage`, `2d20 with advantage`, `(2d6 + 3) * 2`
- A parser output object is stable and deterministic:
  - contains `normalized_expression`
  - contains ordered term list (dice/constants)

### Relevant files
Create/modify:
- `src/mcp_dnd_dice_roller/parser.py`
- `src/mcp_dnd_dice_roller/models.py` (dataclasses / typed structures)
- `tests/test_parser_acceptance.py`
- `tests/test_parser_rejections.py`

### Sub-tasks
1. Define internal models (e.g., `DieTerm`, `ConstantTerm`, `ParsedRollRequest`).
2. Implement normalization (lowercasing, whitespace collapsing, safe punctuation stripping).
3. Implement dice extraction (`NdX` / `dX`) and constant extraction (+/− integers).
4. Detect and remove filler tokens (roll verbs, “with”, “modifier”, etc.).
5. Detect out-of-scope operators (`*`, `/`, parentheses) and reject early.
6. Produce a deterministic `normalized_expression` string.

---

## Parent Task 3 — Validator (Dice Whitelist + Advantage/Disadvantage Rules)

### Purpose
Enforce strict validation rules so invalid/out-of-scope requests fail fast and no roll is performed.

### Functional requirements satisfied
- Spec §4.1: allowed dice set only (`d4,d6,d8,d10,d12,d20,d100`)
- Spec §4.3: advantage/disadvantage d20-only, exactly one `1d20` term when requested
- Spec §4.4: fail-fast validation, stable prefix-coded errors

### Proof artifacts
- Unit tests verifying:
  - `2d7 + 1` fails with message starting `[INVALID_DIE]`
  - `advantage` fails with `[INVALID_ADVANTAGE_USAGE]`
  - `2d20 with advantage` fails with `[INVALID_ADVANTAGE_USAGE]`
  - `(2d6 + 3) * 2` fails with `[OUT_OF_SCOPE_SYNTAX]`
- No RNG calls occur for rejected inputs (can be proven by injecting an RNG spy/stub).

### Relevant files
Create/modify:
- `src/mcp_dnd_dice_roller/validator.py`
- `src/mcp_dnd_dice_roller/errors.py` (error helpers / exception types)
- `tests/test_validation_errors.py`

### Sub-tasks
1. Define a small exception type for “tool hard errors” with code + message formatting.
2. Implement dice whitelist validation.
3. Implement advantage/disadvantage validation (d20-only, exactly one `1d20` when present).
4. Implement out-of-scope syntax checks (if not already enforced by parser).
5. Add tests ensuring error messages have correct prefixes and helpful examples.

---

## Parent Task 4 — Secure RNG + Nonce + Deterministic Test Injection

### Purpose
Provide production-grade randomness (OS entropy) while keeping tests deterministic via dependency injection. Add per-response nonce metadata.

### Functional requirements satisfied
- Spec §6.1: secure and non-reproducible RNG
- Spec §5.3: output includes `rng.source` and `rng.nonce`
- Spec §8.2: deterministic testing without exposing seeds

### Proof artifacts
- Unit test verifying production RNG wrapper reports `source = secrets.SystemRandom`.
- Unit test verifying each result includes a unique `nonce`.
- Unit tests use a deterministic RNG implementation to assert exact roll outcomes.

### Relevant files
Create/modify:
- `src/mcp_dnd_dice_roller/rng.py`
- `src/mcp_dnd_dice_roller/models.py`
- `tests/test_rng.py`

### Sub-tasks
1. Define an RNG interface (e.g., `randint(1, n)` or `roll_die(sides)`).
2. Implement a production RNG wrapper using `secrets.SystemRandom`.
3. Implement a deterministic RNG for tests (fixed sequence).
4. Implement `nonce` generation (UUID recommended).
5. Ensure the tool handler can accept an injected RNG for tests.

---

## Parent Task 5 — Evaluator (Rolling Engine) with Audit Trail Terms

### Purpose
Evaluate parsed, validated expressions into raw rolls, subtotals, and totals, producing the audit trail data required by the spec.

### Functional requirements satisfied
- Spec §4.5 (implied by §5.3): `terms` include raw rolls and subtotals
- Spec §6.3: evaluation strategy
- Spec §8.1 (Evaluation tests): roll bounds, arithmetic correctness

### Proof artifacts
- Unit tests proving totals equal sum of subtotals.
- Unit tests proving each roll is within `[1..sides]` for all allowed dice.
- Deterministic tests for specific expressions using injected deterministic RNG:
  - `2d10 + 2d4 + 4`
  - `d20 - 1`

### Relevant files
Create/modify:
- `src/mcp_dnd_dice_roller/roller.py`
- `src/mcp_dnd_dice_roller/models.py`
- `tests/test_evaluator.py`

### Sub-tasks
1. Implement rolling of standard dice terms (`NdX`) producing `rolls` and `subtotal`.
2. Implement constants/integers as terms.
3. Implement total computation as sum of term subtotals.
4. Add invariants checks (e.g., term subtotal consistency) for internal correctness.
5. Add deterministic unit tests for representative expressions.

---

## Parent Task 6 — d20 Advantage/Disadvantage Evaluation + Audit Detail

### Purpose
Implement advantage/disadvantage behavior for a single d20 term, returning both raw rolls and which roll was kept.

### Functional requirements satisfied
- Spec §4.3: advantage/disadvantage behavior
- Spec §5.3: special d20 adv/disadv term fields (`mode`, `rolls` length 2, `kept` length 1)
- Spec §8.1: adv/disadv selection correctness

### Proof artifacts
- Unit tests (deterministic RNG) verifying:
  - advantage keeps max of two d20 rolls
  - disadvantage keeps min of two d20 rolls
  - term shape includes `mode`, `rolls: [a,b]`, `kept: [chosen]`, `subtotal == chosen`
- A demo request shows both rolls and kept selection in returned JSON.

### Relevant files
Create/modify:
- `src/mcp_dnd_dice_roller/roller.py`
- `src/mcp_dnd_dice_roller/models.py`
- `tests/test_adv_disadv.py`

### Sub-tasks
1. Extend parsed request model to carry `mode: none|advantage|disadvantage`.
2. In evaluator, special-case the validated d20 term when mode is set.
3. Compute `kept` and set `subtotal` accordingly.
4. Add deterministic tests for advantage/disadvantage.
5. Ensure invalid usages are rejected by validator (covered in Parent Task 3).

---

## Parent Task 7 — Formatter: Stable JSON Shape + Single-Line Explanation String

### Purpose
Produce the final tool response with required top-level fields and a deterministic single-line `explanation` string that “shows the math.”

### Functional requirements satisfied
- Spec §5.3–§5.4: output schema and example payload
- Spec §6.4: explanation formatting requirements
- Spec §8.3: golden tests for formatting stability

### Proof artifacts
- Golden tests asserting `explanation` formatting for:
  - `d20`
  - `d20 with disadvantage +5`
  - `2d10 + 2d4 + 4`
- Tool response always includes: `request_id`, `timestamp`, `input`, `normalized_expression`, `rng`, `terms`, `total`, `explanation`.

### Relevant files
Create/modify:
- `src/mcp_dnd_dice_roller/format.py`
- `src/mcp_dnd_dice_roller/server.py`
- `tests/test_explanation_golden.py`

### Sub-tasks
1. Define a canonical response object builder.
2. Implement `explanation` formatting rules for:
   - normal dice terms
   - adv/disadv d20 term
   - constants
3. Ensure deterministic ordering and spacing.
4. Add golden tests for explanation strings.
5. Integrate formatter into MCP tool handler.

---

## Parent Task 8 — End-to-End “roll_dice” Integration + Hard Errors

### Purpose
Wire parser → validator → evaluator → formatter into `roll_dice`, ensuring invalid inputs throw hard MCP tool errors and valid inputs return fully audit-ready responses.

### Functional requirements satisfied
- Spec §4.4: hard error behavior and coded messages
- Spec §5: tool contract end-to-end
- Spec §9.2–§9.6: demoable milestones culminating in working tool

### Proof artifacts
- End-to-end tests (handler-level) for:
  - accepted inputs return complete output schema
  - rejected inputs raise with correct prefix code and contain a helpful example
- Manual demo via Claude Code shows:
  - `2d10 + 2d4 + 4` works
  - `roll a d20 with advantage and a +3 modifier` works
  - `2d7 + 1` fails fast

### Relevant files
Create/modify:
- `src/mcp_dnd_dice_roller/server.py`
- `tests/test_roll_dice_e2e.py`
- `README.md`

### Sub-tasks
1. Implement `roll_dice(text)` pipeline: normalize/parse → validate → roll → format.
2. Ensure exceptions propagate as MCP hard errors.
3. Add handler-level tests for success and failure paths.
4. Update `README.md` with demo commands and expected behaviors.
5. Verify explanation “math shown” meets UX expectations.

---

## Notes / Constraints
- The spec requires **hard errors** for invalid input; do not return `ok:false` payloads.
- Production RNG must not be user-seeded or reproducible.
- Only classic dice are allowed; ensure strict validation.
