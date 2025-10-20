"""
Tests for the simplified pathfinding utilities.
"""

from __future__ import annotations

import pytest

from engine import GameState, SnakeState
from models import Direction, Position
from pathfinding import find_path


class TestFindPath:
    def test_straight_line_path(self, make_state, snake) -> None:
        state = make_state([snake(0, (2, 2))])
        path = find_path(state, 0, Position(2, 2), Position(6, 2))
        assert path is not None
        assert path[-1] == Position(6, 2)

    def test_around_obstacle(self, make_state, snake) -> None:
        obstacle_segments = {(4, 2), (4, 3), (4, 4)}
        blocker = snake(1, *obstacle_segments)
        state = make_state([snake(0, (2, 3)), blocker])
        path = find_path(state, 0, Position(2, 3), Position(6, 3))
        assert path is not None
        obstacle_positions = {Position(x, y) for x, y in obstacle_segments}
        assert all(pos not in obstacle_positions for pos in path)

    def test_returns_none_when_blocked(self, make_state, snake) -> None:
        body = snake(1, (3, 3), (3, 4), (4, 4), (5, 4), (5, 3), (4, 2))
        state = make_state([snake(0, (4, 3)), body])
        path = find_path(state, 0, Position(4, 3), Position(6, 3))
        assert path is None

    def test_can_traverse_tail(self, make_state) -> None:
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

    def test_start_equal_goal_returns_empty_path(self, make_state, snake) -> None:
        state = make_state([snake(0, (4, 4))])
        path = find_path(state, 0, Position(4, 4), Position(4, 4))
        assert path == []

    def test_path_skips_cells_occupied_by_other_snakes(self, make_state, snake) -> None:
        blocker = snake(1, (3, 4), (3, 5), (3, 6))
        state = make_state([snake(0, (2, 5)), blocker])
        path = find_path(state, 0, Position(2, 5), Position(4, 5))
        assert path is not None
        blocked = {Position(3, 4), Position(3, 5), Position(3, 6)}
        assert all(coord not in blocked for coord in path)
