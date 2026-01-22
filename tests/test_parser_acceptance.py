import pytest

from mcp_dnd_dice_roller.models import ConstantTerm, DieTerm
from mcp_dnd_dice_roller.parser import parse_request


@pytest.mark.parametrize(
    ("text", "normalized_expression", "terms"),
    [
        ("d20", "d20", [DieTerm(count=1, sides=20, sign=1, mode="normal")]),
        ("d100", "d100", [DieTerm(count=1, sides=100, sign=1, mode="normal")]),
        (
            "2d10 + 2d4 + 4",
            "2d10 + 2d4 + 4",
            [
                DieTerm(count=2, sides=10, sign=1, mode="normal"),
                DieTerm(count=2, sides=4, sign=1, mode="normal"),
                ConstantTerm(value=4),
            ],
        ),
        (
            "roll a d20 with advantage and a +3 modifier",
            "d20(adv) + 3",
            [
                DieTerm(count=1, sides=20, sign=1, mode="advantage"),
                ConstantTerm(value=3),
            ],
        ),
    ],
)
def test_parse_acceptance(text, normalized_expression, terms):
    parsed = parse_request(text)
    assert parsed.normalized_expression == normalized_expression
    assert parsed.terms == terms
