# MCP D&D Dice Roller (Python) — Implementation Specification

**Date:** 2026-01-22

## 1. Executive Summary
This project is a Python Model Context Protocol (MCP) server that provides **auditable, high-quality dice rolls** for Dungeons & Dragons use inside **Claude Code**.

Users will issue **natural-language** requests like:
- “roll a d20 with advantage and a +3 modifier”
- “2d10 + 2d4 + 4”

The server parses the request, validates it against a strict D&D dice whitelist, performs the roll using OS-backed randomness, and returns:
- a **structured JSON result** (for programmatic consumption)
- a **single explanation string** that shows the full math (raw rolls → kept selection → modifiers → total)

The server **fails fast** (no roll performed) on invalid or out-of-scope requests.

---

## 2. Goals, Non-Goals, and Success Metrics

### 2.1 Goals
- **Simple UX:** a single natural-language input string.
- **Audit trails:** show all underlying rolls and math.
- **Strict dice support:** only classic polyhedral dice are permitted.
- **D&D-style expressions:** support mixed dice + constants (e.g., `2d6 + 1d8 + 3`).
- **d20 advantage/disadvantage:** supported and explicit in the audit trail.
- **Fail-fast validation:** invalid requests produce an MCP tool error (hard error).

### 2.2 Non-Goals
- Not a full D&D rules engine (no crit logic, attack resolution, initiative systems).
- No support for non-standard dice (e.g., `d7`, `d13`).
- No support for complex arithmetic beyond addition/subtraction in v1 (e.g., parentheses, multiplication).
- No reproducible/user-seeded rolls (by design).
- No persistent database/history store (unless added later).

### 2.3 Success Metrics
**Auditability & UX (primary):**
- Every successful roll returns:
  - raw rolls for each die term
  - kept selection for advantage/disadvantage
  - per-term subtotals
  - final `total`
  - an `explanation` string that clearly shows the math

**Correctness:**
- 100% pass on unit tests covering:
  - parsing the supported grammar
  - enforcing the dice whitelist
  - enforcing advantage/disadvantage rules
  - arithmetic correctness for mixed expressions

**Performance (targets; adjustable):**
- p95 tool execution time < 200ms for typical expressions (e.g., `d20+5`, `2d6+3`).

---

## 3. Users, Use Cases, and User Stories

### 3.1 Primary User
- A Claude Code user who wants trustworthy dice rolls with an auditable breakdown.

### 3.2 Use Cases
1. **Simple single die**
   - Input: `d20`
   - Output: one d20 roll with explanation.

2. **Advantage/Disadvantage on d20**
   - Input: “roll a d20 with disadvantage +5 modifier”
   - Output: two d20 rolls, kept roll, +5, final total.

3. **Mixed expression**
   - Input: `2d10 + 2d4 + 4`
   - Output: raw rolls for each term, subtotals, final total.

4. **Validation failure**
   - Input: `2d7 + 1`
   - Output: tool error (hard error), no roll performed.

---

## 4. Functional Requirements

### 4.1 Supported Dice
**Allowed die sizes:** `d4, d6, d8, d10, d12, d20, d100`

Any other die size MUST be rejected.

### 4.2 Supported Expression Grammar (v1)
The server must support:
- Dice terms: `dX` and `NdX` where `N` is a positive integer and `X` is one of the allowed die sizes.
  - Examples: `d20`, `2d6`, `10d8`, `1d12`
- Integer constants with + / -
  - Examples: `+ 4`, `-2`, “+3 modifier”, “plus 3”, “minus 1”
- Addition and subtraction only (no parentheses, multiplication, division)
  - Examples:
    - `2d10 + 2d4 + 4`
    - `d20 - 1`

The parser should tolerate optional roll verbs and filler words (e.g., “roll”, “roll a”, “with”, “modifier”).

### 4.3 Advantage / Disadvantage Rules (v1)
- Advantage/disadvantage are **only valid when a d20 roll is present**.
- If requested, it applies to a **single d20 term of count 1**.

**Normative rule (chosen to enable implementation planning):**
- If the request includes `advantage` or `disadvantage`:
  - The expression MUST contain **exactly one** d20 term with count `1` (i.e., `d20` or `1d20`).
  - Other non-d20 terms (e.g., `+2d6+3`) are allowed.
  - If there is no d20 term: reject.
  - If there are multiple d20 terms or `Nd20` where `N != 1`: reject.

**Behavior:**
- Advantage: roll two d20 values and keep the **higher**.
- Disadvantage: roll two d20 values and keep the **lower**.

### 4.4 Fail-Fast Error Handling
- The MCP tool MUST throw a **hard error** for invalid requests.
- A hard error means **no roll is performed**.

**Error messaging requirement:**
- Error messages MUST:
  - clearly state what failed
  - include a short hint and at least one valid example
  - include a stable prefix code in the message for easier downstream handling

**Recommended error codes (prefix in message):**
- `UNPARSEABLE_INPUT`
- `INVALID_DIE`
- `INVALID_ADVANTAGE_USAGE`
- `OUT_OF_SCOPE_SYNTAX`

Example error message format:
- `[INVALID_DIE] Only d4,d6,d8,d10,d12,d20,d100 are supported. Example: "2d10 + 2d4 + 4".`

---

## 5. MCP Tool Contract

### 5.1 Tools
**v1 exposes one tool:** `roll_dice`

### 5.2 Tool Input Schema
- `text` (string, required): the natural-language roll request.

### 5.3 Tool Output Schema (Successful)
The output MUST include both structured data and a math explanation string.

Minimum required fields:
- `request_id` (string): unique per request
- `timestamp` (string): ISO-8601 UTC
- `input` (string): original input
- `normalized_expression` (string): normalized, machine-generated expression representation
- `rng` (object): RNG metadata
  - `source` (string): e.g., `secrets.SystemRandom`
  - `nonce` (string): unique per response (UUID recommended)
- `terms` (array): evaluated terms in order
- `total` (integer): final total
- `explanation` (string): single-line math breakdown

#### Term object requirements
Each element in `terms` MUST be one of:

**Die term:**
- `type`: `die`
- `count`: integer
- `sides`: integer
- `rolls`: array of integers (length `count`, except d20 adv/disadv special case)
- `subtotal`: integer

**d20 adv/disadv die term (specialization of die term):**
- `type`: `die`
- `count`: `1`
- `sides`: `20`
- `mode`: `advantage | disadvantage`
- `rolls`: array of two integers
- `kept`: array of one integer
- `subtotal`: integer equal to kept value

**Constant term:**
- `type`: `constant`
- `value`: integer
- `subtotal`: integer (same as value)

### 5.4 Output Example
```json
{
  "request_id": "01J3MZ9Q3Y5R8K2N4W8GQK9P2A",
  "timestamp": "2026-01-22T19:03:12Z",
  "input": "roll a d20 with disadvantage +5 modifier",
  "normalized_expression": "d20(disadv) + 5",
  "rng": {
    "source": "secrets.SystemRandom",
    "nonce": "9a2c7f2d-2a32-4fd9-9a2d-0b8e2f2d8a71"
  },
  "terms": [
    {
      "type": "die",
      "count": 1,
      "sides": 20,
      "mode": "disadvantage",
      "rolls": [15, 7],
      "kept": [7],
      "subtotal": 7
    },
    {
      "type": "constant",
      "value": 5,
      "subtotal": 5
    }
  ],
  "total": 12,
  "explanation": "d20(disadv): rolls [15, 7] -> keep 7; +5 => 12"
}
```

---

## 6. Technical Considerations

### 6.1 Randomness (RNG)
Requirement: **secure and non-reproducible** RNG with audit metadata.
- Use OS-backed randomness via Python `secrets` / `secrets.SystemRandom`.
- Include `rng.source` and `rng.nonce` in every response.
- Do not expose seeds or support user-defined seeding.

### 6.2 Parser Strategy
Recommended approach:
- Normalize input (lowercase, strip punctuation where safe, collapse whitespace).
- Detect advantage/disadvantage keywords.
- Extract dice terms using a regex like `(?P<count>\d*)d(?P<sides>\d+)`.
- Extract integer modifiers/constants from remaining tokens.

Strict validation:
- Reject unsupported operators (e.g., `*`, `/`, parentheses) as `OUT_OF_SCOPE_SYNTAX`.
- Reject unsupported dice as `INVALID_DIE`.

### 6.3 Evaluation Strategy
- Convert parsed expression into a simple ordered list of terms.
- Evaluate each term producing raw rolls and a subtotal.
- Sum subtotals into `total`.

### 6.4 Explanation Formatting
- Single-line default, deterministic formatting for golden tests.
- Must clearly show:
  - for each die term: the individual rolls and subtotal
  - for d20 adv/disadv: both rolls, kept value
  - constants/modifiers
  - final equality to total

---

## 7. Security and Compliance Requirements

### 7.1 Input/Output Safety
- Treat input text as potentially sensitive; avoid verbose logging.
- No external network calls required.

### 7.2 Logging
- Default: minimal logs.
- If logging is enabled:
  - never log full user context beyond the roll string
  - never log internal secrets (none expected)

### 7.3 Integrity
- Never alter outcomes after rolling.
- Always include the raw rolls used to compute totals.

---

## 8. Testing Strategy

### 8.1 Unit Tests
- Parsing:
  - Accept:
    - `d20`
    - `d100`
    - `2d10 + 2d4 + 4`
    - “roll a d20 with advantage and a +3 modifier”
  - Reject:
    - `2d7 + 1` (`INVALID_DIE`)
    - `advantage` (no d20 term; `INVALID_ADVANTAGE_USAGE`)
    - `2d20 with advantage` (`INVALID_ADVANTAGE_USAGE`)
    - `(2d6 + 3) * 2` (`OUT_OF_SCOPE_SYNTAX`)

- Evaluation:
  - roll bounds for each die size
  - constant arithmetic
  - adv/disadv selection correctness

### 8.2 Deterministic Testing Without Seeding
To keep production non-reproducible while tests are deterministic:
- implement an RNG interface that can be swapped in tests with a fixed sequence generator.

### 8.3 Golden Tests
- Snapshot tests for `explanation` string formatting and JSON keys/shape.

---

## 9. Demoable Units of Work (with Proof Artifacts)

1. **MCP server skeleton**
   - Proof: Claude Code can invoke `roll_dice` and receive a JSON response.

2. **Parser + validator v1**
   - Proof: unit tests for accepted/rejected phrases.

3. **Roll evaluator + audit trail**
   - Proof: deterministic tests verifying `terms`, `total`, and bounds.

4. **d20 advantage/disadvantage**
   - Proof: tests and demo output showing both rolls and kept selection.

5. **Explanation string**
   - Proof: golden tests for explanation formatting.

6. **Hard-error UX**
   - Proof: invalid inputs reliably throw tool errors with coded messages.

---

## 10. Open Questions / Decisions (Confirm With Stakeholders)
1. **Synonyms support:** Should v1 support “percentile” as `d100`, and “mod” as modifier, and word numbers (“plus five”)?
2. **Whitespace/format tolerance:** How permissive should we be about formats like `2 d 6 +3`?
3. **Multiple d20 terms:** Should expressions like `d20 + d20` be allowed (without adv/disadv), and how should they be represented in output?

---

## 11. Implementation Checklist (Quick Start)
- [ ] Implement MCP server with tool `roll_dice(text: str)`
- [ ] Implement parser → AST/term list + validation
- [ ] Implement secure RNG wrapper + nonce
- [ ] Implement evaluator (including d20 adv/disadv)
- [ ] Implement formatter for structured output + `explanation`
- [ ] Add unit tests + golden tests
