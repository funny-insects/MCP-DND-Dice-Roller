from mcp_dnd_dice_roller.parser import parse_request


def test_parse_is_deterministic():
    text = "roll a d20 with advantage and a +3 modifier"
    a = parse_request(text)
    b = parse_request(text)

    assert a.normalized_input == b.normalized_input
    assert a.mode == b.mode
    assert a.terms == b.terms
    assert a.normalized_expression == b.normalized_expression
