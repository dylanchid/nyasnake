"""
Tests for the simplified pathfinding utilities.
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from engine import GameState, SnakeState
from models import Direction, Position
from pathfinding import find_path


def make_state(
    snakes: list[SnakeState],
    food: set[Position] | None = None,
    width: int = 12,
    height: int = 12,
    frame: int = 0,
) -> GameState:
    occupied = {
        segment: snake.id
        for snake in snakes
        if snake.alive
        for segment in snake.body
    }
    return GameState(
        snakes=tuple(snakes),
        food=frozenset(food or set()),
        occupied=MappingProxyType(occupied),
        width=width,
        height=height,
        frame=frame,
    )


def snake(id_: int, *segments: tuple[int, int], direction: Direction = Direction.RIGHT) -> SnakeState:
    body = tuple(Position(x, y) for x, y in segments)
    return SnakeState(id=id_, body=body, direction=direction)


class TestFindPath:
    def test_straight_line_path(self) -> None:
        state = make_state([snake(0, (2, 2))])
        path = find_path(state, 0, Position(2, 2), Position(6, 2))
        assert path is not None
        assert path[-1] == Position(6, 2)

    def test_around_obstacle(self) -> None:
        obstacle_segments = {(4, 2), (4, 3), (4, 4)}
        blocker = snake(1, *obstacle_segments)
        state = make_state([snake(0, (2, 3)), blocker])
        path = find_path(state, 0, Position(2, 3), Position(6, 3))
        assert path is not None
        obstacle_positions = {Position(x, y) for x, y in obstacle_segments}
        assert all(pos not in obstacle_positions for pos in path)

    def test_returns_none_when_blocked(self) -> None:
        body = snake(1, (3, 3), (3, 4), (4, 4), (5, 4), (5, 3), (4, 2))
        state = make_state([snake(0, (4, 3)), body])
        path = find_path(state, 0, Position(4, 3), Position(6, 3))
        assert path is None

    def test_can_traverse_tail(self) -> None:
        player = SnakeState(
            id=0,
            body=(
                Position(2, 2),
                Position(1, 2),
                Position(1, 3),
                Position(2, 3),
            ),
            direction=Direction.RIGHT,
        )
        state = make_state([player])
        path = find_path(state, 0, Position(2, 2), Position(1, 3))
        assert path is not None
        assert Position(1, 3) in path
