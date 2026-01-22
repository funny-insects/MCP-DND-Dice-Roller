from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


ALLOWED_DIE_SIDES: set[int] = {4, 6, 8, 10, 12, 20, 100}

Mode: TypeAlias = Literal["advantage", "disadvantage", "none"]
DieMode: TypeAlias = Literal["advantage", "disadvantage", "normal"]
Sign: TypeAlias = Literal[1, -1]


@dataclass(frozen=True)
class DieTerm:
    count: int
    sides: int
    sign: Sign = 1
    mode: DieMode = "normal"


@dataclass(frozen=True)
class ConstantTerm:
    value: int


ParsedTerm: TypeAlias = DieTerm | ConstantTerm


@dataclass(frozen=True)
class ParsedRollRequest:
    input: str
    normalized_input: str
    mode: Mode
    terms: list[ParsedTerm]
    normalized_expression: str
