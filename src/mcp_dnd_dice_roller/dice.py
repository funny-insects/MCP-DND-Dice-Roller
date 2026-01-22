from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from .errors import DiceError
from .models import ConstantTerm, DieTerm
from .parser import parse_request


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_roll_request(text: str):
    """Parse and normalize only (no RNG)."""

    return parse_request(text)


def roll_from_text(text: str) -> dict[str, Any]:
    """Parse, validate, then roll. Raises DiceError for invalid input."""

    parsed = parse_request(text)
    terms = parsed.terms

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
        subtotal = term.sign * sum(rolls)
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
                sign_prefix = "-" if t["subtotal"] < 0 else ""
                explanation_parts.append(
                    f"{sign_prefix}{prefix}: rolls {t['rolls']} => {t['subtotal']}"
                )

    explanation = "; ".join(explanation_parts) + f" => {total}"

    return {
        "request_id": uuid.uuid4().hex,
        "timestamp": _now_utc_iso(),
        "input": text,
        "normalized_expression": parsed.normalized_expression,
        "rng": {
            "source": "secrets.SystemRandom",
            "nonce": str(uuid.uuid4()),
        },
        "terms": evaluated_terms,
        "total": total,
        "explanation": explanation,
    }
