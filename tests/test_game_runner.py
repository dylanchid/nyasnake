from __future__ import annotations

from random import Random
from typing import Mapping, Optional, Sequence

import pytest

from config import AIConfig, AIPersonality, DebugConfig, DisplayConfig, GameConfig
from factories import AIControllerFactory
from game import (
    GameRunner,
    InputCommand,
    InputProvider,
    MoveCommand,
    Renderer,
    SnakeController,
    SnakeProfile,
)
from models import Direction


class DummyRenderer(Renderer):
    def __init__(self, display_config: DisplayConfig, debug_config: DebugConfig) -> None:
        super().__init__(display_config, debug_config)
        self.calls = 0
        self.events: Optional[Sequence] = None

    def render(self, state, profiles, events) -> None:  # type: ignore[override]
        self.calls += 1
        self.events = events


class DummyInput(InputProvider):
    def __init__(self, commands: Optional[Sequence[InputCommand]] = None) -> None:
        self._commands = list(commands or [])

    def poll(self) -> Sequence[InputCommand]:  # type: ignore[override]
        return tuple(self._commands)


class StaticDecisionProvider:
    def __init__(self, decisions: Mapping[int, Direction]) -> None:
        self._decisions = dict(decisions)

    def decide(self, state) -> Mapping[int, Direction]:  # type: ignore[override]
        return dict(self._decisions)


class FixedController(SnakeController):
    def __init__(self, direction: Direction) -> None:
        self.direction = direction
        self.calls = 0

    def decide(self, state, snake) -> Optional[Direction]:  # type: ignore[override]
        self.calls += 1
        return self.direction


def build_profiles(display_config: DisplayConfig) -> list[SnakeProfile]:
    return [
        SnakeProfile(id=0, personality=AIPersonality.AGGRESSIVE, color=display_config.COLORS["red"], symbol="A"),
        SnakeProfile(id=1, personality=AIPersonality.DEFENSIVE, color=display_config.COLORS["green"], symbol="B"),
        SnakeProfile(id=2, personality=AIPersonality.BALANCED, color=display_config.COLORS["blue"], symbol="C"),
    ]


@pytest.fixture
def configs() -> tuple[GameConfig, DisplayConfig, DebugConfig, AIConfig]:
    return GameConfig(MAX_ROUNDS=1), DisplayConfig(), DebugConfig(), AIConfig()


def test_controller_override_supersedes_ai(configs):
    game_config, display_config, debug_config, _ai_config = configs
    renderer = DummyRenderer(display_config, debug_config)
    input_provider = DummyInput()
    ai = StaticDecisionProvider({0: Direction.RIGHT, 1: Direction.LEFT, 2: Direction.UP})
    controller = FixedController(Direction.DOWN)

    runner = GameRunner(
        profiles=build_profiles(display_config),
        renderer=renderer,
        input_provider=input_provider,
        ai_controller=ai,
        controller_overrides={0: controller},
        game_config=game_config,
        display_config=display_config,
        debug_config=debug_config,
        tick_interval=0.0,
        rng=Random(0),
        state_history_capacity=4,
    )

    runner.run()

    command_history = runner.command_history
    assert command_history
    assert any(isinstance(cmd, MoveCommand) and cmd.direction == Direction.DOWN for cmd in command_history[0])
    assert controller.calls >= 1


def test_event_listeners_receive_ticks(configs):
    game_config, display_config, debug_config, ai_config = configs
    renderer = DummyRenderer(display_config, debug_config)
    ai_factory = AIControllerFactory(ai_config)
    profiles = build_profiles(display_config)
    ai_controller = ai_factory.create("normal", profiles)
    captured = []

    runner = GameRunner(
        profiles=profiles,
        renderer=renderer,
        input_provider=DummyInput(),
        ai_controller=ai_controller,
        game_config=game_config,
        display_config=display_config,
        debug_config=debug_config,
        event_listeners=[captured.append],
        tick_interval=0.0,
        rng=Random(0),
    )

    runner.run()

    assert captured, "Expected at least one tick result to be captured"
    assert renderer.calls >= 1
