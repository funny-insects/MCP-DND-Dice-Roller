from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .dice import DiceError, roll_from_text


mcp = FastMCP("mcp-dnd-dice-roller")


@mcp.tool()
def roll_dice(text: str):
    """Roll D&D dice from a natural-language request.

    Input: text (string)
    Output: structured JSON with audit details + explanation

    Raises a hard error (exception) on invalid input.
    """

    try:
        return roll_from_text(text)
    except DiceError as e:
        # Fail-fast: surface stable error codes in the message.
        raise ValueError(str(e)) from None


def run() -> None:
    # Default transport is stdio, which works well for Claude Code MCP integration.
    mcp.run()


if __name__ == "__main__":
    run()
