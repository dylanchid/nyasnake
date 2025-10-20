"""
Smoke tests for the CLI entry point to ensure wiring stays intact.
"""

from __future__ import annotations

import logging

import pytest

import main
from ai import GreedyAIController
from config import AIPersonality
from engine import SnakeState
from game import AnsiRenderer
from models import Direction, Position


@pytest.fixture
def stub_state(make_state):
    return make_state(
        [
            SnakeState(id=0, body=(Position(4, 4),), direction=Direction.RIGHT, score=20),
            SnakeState(id=1, body=(Position(6, 6),), direction=Direction.LEFT, alive=False),
            SnakeState(id=2, body=(Position(7, 7),), direction=Direction.UP, alive=False),
        ],
        frame=5,
    )


def test_main_wires_factories(monkeypatch, capsys, stub_state):
    recorded = {}

    class StubRunner:
        def __init__(self, profiles, *_, **kwargs):  # type: ignore[override]
            recorded["kwargs"] = kwargs
            self._profiles = {profile.id: profile for profile in profiles}
            self._seed = kwargs.get("seed")
            self._state = stub_state

        def run(self) -> None:
            pass

        @property
        def state(self):
            return self._state

        @property
        def profiles(self):
            return self._profiles

        @property
        def seed(self):
            return self._seed

    monkeypatch.setattr(main, "GameRunner", StubRunner)
    monkeypatch.setattr(main, "setup_logging", lambda level: logging.getLogger("test").setLevel(level))
    monkeypatch.setattr(main, "create_input_provider", lambda interactive: None)
    monkeypatch.setattr(main.sys, "argv", ["nyasnake", "--seed", "7", "--tick-rate", "2", "--ai-level", "hard"])

    main.main()

    output = capsys.readouterr().out
    assert "Nyasnake Arena" in output
    assert "Winner" in output

    kwargs = recorded["kwargs"]
    controller = kwargs["ai_controller"]
    assert isinstance(controller, GreedyAIController)
    renderer = kwargs["renderer"]
    assert isinstance(renderer, AnsiRenderer)
    strategies = {sid: strategy.personality for sid, strategy in controller._strategies.items()}  # type: ignore[attr-defined]
    assert set(strategies.values()) == {AIPersonality.AGGRESSIVE}
