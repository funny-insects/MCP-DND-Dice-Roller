from __future__ import annotations

import re

from .errors import DiceError
from .models import ALLOWED_DIE_SIDES, ConstantTerm, DieTerm, Mode, ParsedRollRequest, ParsedTerm


_FILLER_WORDS = {
    "roll",
    "a",
    "an",
    "the",
    "with",
    "please",
    "and",
    "mod",
    "modifier",
}

_DICE_RE = re.compile(r"^(?P<count>\d*)d(?P<sides>\d+)$")


def normalize_text(text: str) -> str:
    s = text.strip().lower()

    # Convert word-operators into symbolic ones.
    s = re.sub(r"\bplus\b", "+", s)
    s = re.sub(r"\bminus\b", "-", s)

    # Replace most punctuation with spaces, but keep + - and alphanumerics.
    s = re.sub(r"[^a-z0-9+\-\s]", " ", s)

    # Ensure + / - are tokenized.
    s = re.sub(r"([+-])", r" \1 ", s)

    # Collapse whitespace.
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _detect_mode(text: str) -> Mode:
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


def _reject_out_of_scope_syntax(raw_text: str) -> None:
    if any(op in raw_text for op in ("*", "/", "(", ")")):
        raise DiceError(
            "[OUT_OF_SCOPE_SYNTAX] Only + and - are supported (no *, /, or parentheses). Example: '2d10 + 2d4 + 4'."
        )


def _build_normalized_expression(terms: list[ParsedTerm]) -> str:
    chunks: list[str] = []

    def append_signed(piece: str, sign: int) -> None:
        if not chunks:
            chunks.append(f"- {piece}" if sign < 0 else piece)
            return
        chunks.append(f"- {piece}" if sign < 0 else f"+ {piece}")

    for term in terms:
        if isinstance(term, DieTerm):
            if term.mode == "normal":
                base = f"{term.count}d{term.sides}" if term.count != 1 else f"d{term.sides}"
                append_signed(base, term.sign)
            else:
                short = "adv" if term.mode == "advantage" else "disadv"
                append_signed(f"d20({short})", 1)
        else:
            append_signed(str(abs(term.value)), 1 if term.value >= 0 else -1)

    expr = " ".join(chunks).strip()
    return re.sub(r"\s+", " ", expr)


def parse_request(text: str) -> ParsedRollRequest:
    if not text or not text.strip():
        raise DiceError(
            "[UNPARSEABLE_INPUT] Empty input. Example: '2d6 + 3' or 'd20 with advantage +5'."
        )

    # Reject out-of-scope syntax BEFORE normalization, so parentheses are still visible.
    _reject_out_of_scope_syntax(text)

    normalized = normalize_text(text)
    mode = _detect_mode(normalized)

    tokens = [t for t in normalized.split(" ") if t and t not in _FILLER_WORDS]

    terms: list[ParsedTerm] = []
    sign: int = 1

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

            terms.append(DieTerm(count=count, sides=sides, sign=1 if sign >= 0 else -1))
            sign = 1
            continue

        if tok.isdigit():
            terms.append(ConstantTerm(value=(1 if sign >= 0 else -1) * int(tok)))
            sign = 1
            continue

        if tok in {"advantage", "disadvantage"}:
            continue

        raise DiceError(
            f"[UNPARSEABLE_INPUT] Could not understand token '{tok}'. Example: '2d6 + 3' or 'd20 with advantage +5'."
        )

    if mode != "none":
        d20_terms = [t for t in terms if isinstance(t, DieTerm) and t.sides == 20]
        if len(d20_terms) != 1 or d20_terms[0].count != 1 or d20_terms[0].sign != 1:
            raise DiceError(
                "[INVALID_ADVANTAGE_USAGE] Advantage/disadvantage requires exactly one 'd20' (or '1d20') term. Example: 'd20 with advantage +3'."
            )

        updated: list[ParsedTerm] = []
        for t in terms:
            if isinstance(t, DieTerm) and t.sides == 20:
                updated.append(DieTerm(count=1, sides=20, sign=1, mode=mode))
            else:
                updated.append(t)
        terms = updated

    if not terms:
        if mode != "none":
            raise DiceError(
                "[INVALID_ADVANTAGE_USAGE] Advantage/disadvantage requires exactly one 'd20' (or '1d20') term. Example: 'd20 with advantage +3'."
            )
        raise DiceError(
            "[UNPARSEABLE_INPUT] No dice or modifiers found. Example: 'd20' or '2d6 + 3'."
        )

    normalized_expression = _build_normalized_expression(terms)

    return ParsedRollRequest(
        input=text,
        normalized_input=normalized,
        mode=mode,
        terms=terms,
        normalized_expression=normalized_expression,
    )
