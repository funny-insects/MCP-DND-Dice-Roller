import pytest

from mcp_dnd_dice_roller.errors import DiceError
from mcp_dnd_dice_roller.parser import parse_request


@pytest.mark.parametrize(
    ("text", "prefix"),
    [
        ("2d7 + 1", "[INVALID_DIE]"),
        ("advantage", "[INVALID_ADVANTAGE_USAGE]"),
        ("2d20 with advantage", "[INVALID_ADVANTAGE_USAGE]"),
        ("(2d6 + 3) * 2", "[OUT_OF_SCOPE_SYNTAX]"),
    ],
)
def test_parse_rejections(text, prefix):
    with pytest.raises(DiceError) as exc:
        parse_request(text)
    assert str(exc.value).startswith(prefix)
