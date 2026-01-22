from __future__ import annotations

import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal


ALLOWED_DIE_SIDES: set[int] = {4, 6, 8, 10, 12, 20, 100}


class DiceError(ValueError):
    """User-facing validation errors (fail-fast, no roll performed)."""


@dataclass(frozen=True)
class DieTerm:
    count: int
    sides: int
    mode: Literal["advantage", "disadvantage", "normal"] = "normal"


@dataclass(frozen=True)
class ConstantTerm:
    value: int


ParsedTerm = DieTerm | ConstantTerm


_FILLER_WORDS = {
    "roll",
    "a",
    "an",
    "the",
    "with",
    "please",
    "mod",
    "modifier",
}


_DICE_RE = re.compile(r"^(?P<count>\d*)d(?P<sides>\d+)$")


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_text(text: str) -> str:
    s = text.strip().lower()
    s = s.replace(",", " ")

    # Convert word-operators into symbolic ones.
    s = re.sub(r"\bplus\b", "+", s)
    s = re.sub(r"\bminus\b", "-", s)

    # Ensure + / - are tokenized.
    s = re.sub(r"([+-])", r" \1 ", s)

    # Collapse whitespace.
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _detect_mode(text: str) -> Literal["advantage", "disadvantage", "none"]:
    has_adv = re.search(r"\badvantage\b", text) is not None
    has_dis = re.search(r"\bdisadvantage\b", text) is not None
    if has_adv and has_dis:
        raise DiceError(
            "[UNPARSEABLE_INPUT] Found both 'advantage' and 'disadvantage'. Use only one. Example: 'd20 with advantage +3'."
        )
    if has_adv:
        return "advantage"
    if has_dis:
        return "disadvantage"
    return "none"


def _reject_out_of_scope_syntax(text: str) -> None:
    if any(op in text for op in ("*", "/", "(", ")")):
        raise DiceError(
            "[OUT_OF_SCOPE_SYNTAX] Only + and - are supported (no *, /, or parentheses). Example: '2d10 + 2d4 + 4'."
        )


def parse_request(text: str) -> tuple[str, list[ParsedTerm], Literal["advantage", "disadvantage", "none"]]:
    if not text or not text.strip():
        raise DiceError(
            "[UNPARSEABLE_INPUT] Empty input. Example: '2d6 + 3' or 'd20 with advantage +5'."
        )

    normalized = _normalize_text(text)
    _reject_out_of_scope_syntax(normalized)
    mode = _detect_mode(normalized)

    tokens = [t for t in normalized.split(" ") if t and t not in _FILLER_WORDS]

    terms: list[ParsedTerm] = []
    sign = 1

    for tok in tokens:
        if tok == "+":
            sign = 1
            continue
        if tok == "-":
            sign = -1
            continue

        m = _DICE_RE.match(tok)
        if m:
            count_str = m.group("count")
            count = int(count_str) if count_str else 1
            sides = int(m.group("sides"))

            if sides not in ALLOWED_DIE_SIDES:
                raise DiceError(
                    "[INVALID_DIE] Only d4,d6,d8,d10,d12,d20,d100 are supported. Example: '2d10 + 2d4 + 4'."
                )
            if count <= 0:
                raise DiceError(
                    "[UNPARSEABLE_INPUT] Dice count must be a positive integer. Example: '2d6 + 3'."
                )
            if sign == -1:
                raise DiceError(
                    "[OUT_OF_SCOPE_SYNTAX] Subtracting dice terms is not supported. Example: 'd20 - 1'."
                )

            terms.append(DieTerm(count=count, sides=sides))
            sign = 1
            continue

        if tok.isdigit():
            terms.append(ConstantTerm(value=sign * int(tok)))
            sign = 1
            continue

        # Ignore leftover words like 'advantage'/'disadvantage' here (already detected).
        if tok in {"advantage", "disadvantage"}:
            continue

        # Anything else is unparseable.
        raise DiceError(
            f"[UNPARSEABLE_INPUT] Could not understand token '{tok}'. Example: '2d6 + 3' or 'd20 with advantage +5'."
        )

    if not terms:
        raise DiceError(
            "[UNPARSEABLE_INPUT] No dice or modifiers found. Example: 'd20' or '2d6 + 3'."
        )

    if mode != "none":
        d20_terms = [t for t in terms if isinstance(t, DieTerm) and t.sides == 20]
        if len(d20_terms) != 1 or d20_terms[0].count != 1:
            raise DiceError(
                "[INVALID_ADVANTAGE_USAGE] Advantage/disadvantage requires exactly one 'd20' (or '1d20') term. Example: 'd20 with advantage +3'."
            )

        updated: list[ParsedTerm] = []
        for t in terms:
            if isinstance(t, DieTerm) and t.sides == 20:
                updated.append(DieTerm(count=1, sides=20, mode=mode))
            else:
                updated.append(t)
        terms = updated

    return normalized, terms, mode


def _build_normalized_expression(terms: list[ParsedTerm]) -> str:
    chunks: list[str] = []
    for term in terms:
        if isinstance(term, DieTerm):
            if term.mode == "normal":
                chunk = f"{term.count}d{term.sides}" if term.count != 1 else f"d{term.sides}"
            else:
                short = "adv" if term.mode == "advantage" else "disadv"
                chunk = f"d20({short})"
            chunks.append(chunk)
        else:
            if term.value >= 0:
                chunks.append(f"+ {term.value}")
            else:
                chunks.append(f"- {abs(term.value)}")

    # Normalize so it's always readable.
    expr = " ".join(chunks).strip()
    return re.sub(r"\s+", " ", expr)


def roll_from_text(text: str) -> dict[str, Any]:
    """Parse, validate, then roll. Raises DiceError for invalid input."""

    normalized, terms, _mode = parse_request(text)

    rng = secrets.SystemRandom()
    evaluated_terms: list[dict[str, Any]] = []

    for term in terms:
        if isinstance(term, ConstantTerm):
            evaluated_terms.append(
                {
                    "type": "constant",
                    "value": term.value,
                    "subtotal": term.value,
                }
            )
            continue

        if term.mode in ("advantage", "disadvantage"):
            a = rng.randint(1, 20)
            b = rng.randint(1, 20)
            kept = max(a, b) if term.mode == "advantage" else min(a, b)
            evaluated_terms.append(
                {
                    "type": "die",
                    "count": 1,
                    "sides": 20,
                    "mode": term.mode,
                    "rolls": [a, b],
                    "kept": [kept],
                    "subtotal": kept,
                }
            )
            continue

        rolls = [rng.randint(1, term.sides) for _ in range(term.count)]
        subtotal = sum(rolls)
        evaluated_terms.append(
            {
                "type": "die",
                "count": term.count,
                "sides": term.sides,
                "rolls": rolls,
                "subtotal": subtotal,
            }
        )

    total = sum(t["subtotal"] for t in evaluated_terms)

    explanation_parts: list[str] = []
    for t in evaluated_terms:
        if t["type"] == "constant":
            explanation_parts.append(f"{t['value']:+d}")
        else:
            if t.get("mode") in ("advantage", "disadvantage"):
                short = "adv" if t["mode"] == "advantage" else "disadv"
                explanation_parts.append(
                    f"d20({short}): rolls {t['rolls']} -> keep {t['kept'][0]}"
                )
            else:
                prefix = f"{t['count']}d{t['sides']}" if t["count"] != 1 else f"d{t['sides']}"
                explanation_parts.append(f"{prefix}: rolls {t['rolls']} => {t['subtotal']}")

    explanation = "; ".join(explanation_parts) + f" => {total}"

    return {
        "request_id": uuid.uuid4().hex,
        "timestamp": _now_utc_iso(),
        "input": text,
        "normalized_expression": _build_normalized_expression(terms),
        "rng": {
            "source": "secrets.SystemRandom",
            "nonce": str(uuid.uuid4()),
        },
        "terms": evaluated_terms,
        "total": total,
        "explanation": explanation,
    }
