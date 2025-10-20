"""
Tests for factory helpers that assemble controllers and renderers.
"""

from __future__ import annotations

import pytest

from ai import GreedyAIController
from config import AIConfig, AIPersonality, DebugConfig, DisplayConfig
from factories import AIControllerFactory, RendererFactory
from game import AnsiRenderer, SnakeProfile


def make_profiles(display: DisplayConfig) -> list[SnakeProfile]:
    colors = display.COLORS
    return [
        SnakeProfile(id=0, personality=AIPersonality.BALANCED, color=colors["red"], symbol="A"),
        SnakeProfile(id=1, personality=AIPersonality.DEFENSIVE, color=colors["green"], symbol="B"),
        SnakeProfile(id=2, personality=AIPersonality.AGGRESSIVE, color=colors["blue"], symbol="C"),
    ]


@pytest.mark.parametrize("level", ["easy", "normal", "hard"])
def test_ai_controller_factory_assigns_personalities(level: str) -> None:
    display = DisplayConfig()
    profiles = make_profiles(display)
    factory = AIControllerFactory(AIConfig())

    controller = factory.create(level, profiles)

    assert isinstance(controller, GreedyAIController)
    personalities = {sid: strategy.personality for sid, strategy in controller._strategies.items()}  # type: ignore[attr-defined]
    if level == "normal":
        expected = {profile.id: profile.personality for profile in profiles}
    elif level == "easy":
        expected = {profile.id: AIPersonality.DEFENSIVE for profile in profiles}
    else:  # hard
        expected = {profile.id: AIPersonality.AGGRESSIVE for profile in profiles}
    assert personalities == expected


def test_renderer_factory_returns_default_renderer() -> None:
    display = DisplayConfig()
    debug = DebugConfig()
    factory = RendererFactory(display, debug)

    renderer = factory.create("ansi")

    assert isinstance(renderer, AnsiRenderer)
    assert renderer.display_config is display
    assert renderer.debug_config is debug


def test_renderer_factory_unknown_type() -> None:
    factory = RendererFactory(DisplayConfig(), DebugConfig())

    with pytest.raises(ValueError):
        factory.create("unknown")
