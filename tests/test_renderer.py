"""Tests for the ANSI renderer output."""

from __future__ import annotations

from config import AIPersonality, DebugConfig, DisplayConfig
from engine import SnakeState
from game import AnsiRenderer, SnakeProfile
from models import Direction, Position


def test_ansi_renderer_prints_status(make_state, capsys) -> None:
    display = DisplayConfig()
    debug = DebugConfig(LOG_DECISIONS=False)
    renderer = AnsiRenderer(display, debug)

    snake = SnakeState(
        id=0,
        body=(Position(3, 3),),
        direction=Direction.RIGHT,
        score=15,
    )
    state = make_state([snake], width=8, height=6, frame=3)
    profiles = {
        0: SnakeProfile(
            id=0,
            personality=AIPersonality.BALANCED,
            color=display.COLORS["red"],
            symbol="A",
        )
    }

    renderer.render(state, profiles, ())

    out = capsys.readouterr().out
    assert "Nyasnake" not in out  # renderer should not print CLI banners
    assert "Frame: 3" in out
    assert "BALANCED" in out
    assert "Score:   15" in out
