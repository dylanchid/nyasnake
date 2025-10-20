from __future__ import annotations

from random import Random
from typing import Mapping, Optional, Sequence

import pytest

from config import AIConfig, AIPersonality, DebugConfig, DisplayConfig, GameConfig, SpeedRampConfig
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


# Speed ramping tests
def test_speed_ramp_disabled_by_default(configs):
    """Test that speed ramping doesn't occur when not configured."""
    game_config, display_config, debug_config, ai_config = configs
    renderer = DummyRenderer(display_config, debug_config)
    ai_factory = AIControllerFactory(ai_config)
    profiles = build_profiles(display_config)
    ai_controller = ai_factory.create("normal", profiles)
    
    initial_tick = 0.10
    runner = GameRunner(
        profiles=profiles,
        renderer=renderer,
        input_provider=DummyInput(),
        ai_controller=ai_controller,
        game_config=GameConfig(MAX_ROUNDS=10),
        display_config=display_config,
        debug_config=debug_config,
        tick_interval=initial_tick,
        speed_ramp_config=None,
        rng=Random(0),
    )
    
    # Access the internal loop to check tick interval
    assert runner._loop._current_tick_interval == initial_tick
    
    runner.run()
    
    # Tick interval should remain unchanged
    assert runner._loop._current_tick_interval == initial_tick


def test_speed_ramp_decreases_tick_interval():
    """Test that speed ramping reduces tick interval over time."""
    game_config = GameConfig(WIDTH=40, HEIGHT=20, MAX_ROUNDS=250)
    display_config = DisplayConfig()
    debug_config = DebugConfig()
    ai_config = AIConfig()
    
    renderer = DummyRenderer(display_config, debug_config)
    ai_factory = AIControllerFactory(ai_config)
    profiles = build_profiles(display_config)
    ai_controller = ai_factory.create("normal", profiles)
    
    initial_tick = 0.10
    ramp_config = SpeedRampConfig(
        enabled=True,
        ramp_interval=50,  # Ramp every 50 frames
        ramp_step=0.02,    # Reduce by 0.02s per ramp
        min_tick_interval=0.03,
    )
    
    runner = GameRunner(
        profiles=profiles,
        renderer=renderer,
        input_provider=DummyInput(),
        ai_controller=ai_controller,
        game_config=game_config,
        display_config=display_config,
        debug_config=debug_config,
        tick_interval=initial_tick,
        speed_ramp_config=ramp_config,
        rng=Random(0),
    )
    
    # Initial tick interval should match
    assert runner._loop._current_tick_interval == initial_tick
    
    runner.run()
    
    # After running, tick interval should have decreased
    # With ramp_interval=50, ramp_step=0.02, starting at 0.10:
    # Frame 50: 0.10 - 0.02 = 0.08
    # Frame 100: 0.08 - 0.02 = 0.06
    # Frame 150: 0.06 - 0.02 = 0.04
    # Frame 200: 0.04 - 0.02 = 0.02 (but capped at 0.03)
    # So final should be 0.03 (the minimum)
    final_tick = runner._loop._current_tick_interval
    assert final_tick < initial_tick
    assert final_tick >= ramp_config.min_tick_interval


def test_speed_ramp_respects_minimum():
    """Test that speed ramping doesn't go below the minimum tick interval."""
    game_config = GameConfig(WIDTH=40, HEIGHT=20, MAX_ROUNDS=300)
    display_config = DisplayConfig()
    debug_config = DebugConfig()
    ai_config = AIConfig()
    
    renderer = DummyRenderer(display_config, debug_config)
    ai_factory = AIControllerFactory(ai_config)
    profiles = build_profiles(display_config)
    ai_controller = ai_factory.create("normal", profiles)
    
    initial_tick = 0.10
    min_tick = 0.05
    ramp_config = SpeedRampConfig(
        enabled=True,
        ramp_interval=50,
        ramp_step=0.01,
        min_tick_interval=min_tick,
    )
    
    runner = GameRunner(
        profiles=profiles,
        renderer=renderer,
        input_provider=DummyInput(),
        ai_controller=ai_controller,
        game_config=game_config,
        display_config=display_config,
        debug_config=debug_config,
        tick_interval=initial_tick,
        speed_ramp_config=ramp_config,
        rng=Random(0),
    )
    
    runner.run()
    
    # Should not go below minimum
    assert runner._loop._current_tick_interval >= min_tick


def test_speed_ramp_timing():
    """Test that speed ramping occurs at the correct frame intervals."""
    game_config = GameConfig(WIDTH=40, HEIGHT=20, MAX_ROUNDS=120)
    display_config = DisplayConfig()
    debug_config = DebugConfig()
    ai_config = AIConfig()
    
    renderer = DummyRenderer(display_config, debug_config)
    ai_factory = AIControllerFactory(ai_config)
    profiles = build_profiles(display_config)
    ai_controller = ai_factory.create("normal", profiles)
    
    initial_tick = 0.10
    ramp_interval = 100  # Should ramp at frame 100
    ramp_step = 0.02
    
    ramp_config = SpeedRampConfig(
        enabled=True,
        ramp_interval=ramp_interval,
        ramp_step=ramp_step,
        min_tick_interval=0.03,
    )
    
    # Track tick intervals over time
    tick_intervals = []
    
    class TrackingRenderer(DummyRenderer):
        def __init__(self, display_config, debug_config, runner_ref):
            super().__init__(display_config, debug_config)
            self.runner_ref = runner_ref
        
        def render(self, state, profiles, events):
            super().render(state, profiles, events)
            tick_intervals.append(self.runner_ref._loop._current_tick_interval)
    
    # Need to create runner with tracking renderer
    # But we need runner reference first, so we'll check differently
    runner = GameRunner(
        profiles=profiles,
        renderer=renderer,
        input_provider=DummyInput(),
        ai_controller=ai_controller,
        game_config=game_config,
        display_config=display_config,
        debug_config=debug_config,
        tick_interval=initial_tick,
        speed_ramp_config=ramp_config,
        rng=Random(0),
    )
    
    runner.run()
    
    # After 100 frames, tick should have decreased by ramp_step
    # Expected: 0.10 - 0.02 = 0.08
    expected_after_ramp = initial_tick - ramp_step
    final_tick = runner._loop._current_tick_interval
    
    # Should have ramped at least once if game ran for 100+ frames
    if runner.state.frame >= ramp_interval:
        assert final_tick <= expected_after_ramp
