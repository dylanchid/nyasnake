"""
Unit tests for game support components (decision collection, history, events).
"""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Dict, Mapping, Optional, Sequence

import pytest

from game import (
    DecisionCollector,
    EventDispatcher,
    GameEventVisitor,
    InputCommand,
    InputProvider,
    MoveCommand,
    SnakeController,
    StateHistory,
)
from engine import GameEvent, TickResult
from models import Direction


class _StaticDecisionProvider:
    def __init__(self, decisions: Mapping[int, Direction]):
        self._decisions = dict(decisions)

    def decide(self, state) -> Mapping[int, Direction]:  # type: ignore[override]
        return dict(self._decisions)


class _StaticInput(InputProvider):
    def __init__(self, commands: Sequence[InputCommand]):
        self._commands = list(commands)

    def poll(self) -> Sequence[InputCommand]:  # type: ignore[override]
        return tuple(self._commands)


@dataclass
class _FixedController(SnakeController):
    direction: Direction

    def decide(self, state, snake) -> Optional[Direction]:  # type: ignore[override]
        return self.direction


def test_decision_collector_applies_commands_and_overrides(make_state, snake) -> None:
    snakes = [
        snake(0, (3, 3)),
        snake(1, (5, 5)),
    ]
    state = make_state(snakes)
    base_decisions = {0: Direction.UP, 1: Direction.UP}
    collector = DecisionCollector(
        decision_provider=_StaticDecisionProvider(base_decisions),
        input_provider=_StaticInput([MoveCommand(0, Direction.LEFT)]),
        overrides={1: _FixedController(Direction.DOWN)},
    )

    decisions = collector.collect(state)

    assert decisions[0] == Direction.LEFT
    assert decisions[1] == Direction.DOWN
    history = collector.history()
    assert len(history) == 1
    assert {cmd.direction for cmd in history[0]} == {Direction.LEFT, Direction.DOWN}


def test_decision_collector_updates_and_removes_overrides(make_state, snake) -> None:
    snakes = [snake(0, (3, 3)), snake(1, (5, 5))]
    state = make_state(snakes)
    collector = DecisionCollector(
        decision_provider=_StaticDecisionProvider({0: Direction.UP, 1: Direction.UP}),
        input_provider=_StaticInput([]),
        overrides={1: _FixedController(Direction.LEFT)},
    )

    collector.collect(state)
    collector.remove_override(1)
    decisions = collector.collect(state)

    assert decisions[1] == Direction.UP
    assert len(collector.history()) == 2


def test_state_history_tracks_capacity_and_rewind(make_state, snake) -> None:
    history = StateHistory(capacity=2)
    states = [
        make_state([snake(0, (2, 2))], frame=frame)
        for frame in range(3)
    ]
    for state in states:
        history.record(state)

    snapshots = history.snapshots()
    assert [memento.frame for memento in snapshots] == [1, 2]

    latest = history.rewind(1)
    assert latest is not None and latest.frame == 2
    assert len(history.snapshots()) == 1


def test_event_dispatcher_notifies_visitors_and_listeners(make_state, snake) -> None:
    events_captured: list[GameEvent] = []
    ticks_captured: list[TickResult] = []

    class CollectorVisitor(GameEventVisitor):
        def visit(self, event: GameEvent) -> None:
            events_captured.append(event)

    dispatcher = EventDispatcher()
    dispatcher.register_visitor(CollectorVisitor())
    dispatcher.register_listener(ticks_captured.append)

    state = make_state([snake(0, (3, 3))])
    events = (
        GameEvent(type="food_consumed", snake_id=0),
        GameEvent(type="snake_died", snake_id=1),
    )
    tick = TickResult(state=state, events=events)

    dispatcher.dispatch(tick)

    assert ticks_captured == [tick]
    assert events_captured == list(events)
