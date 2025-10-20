"""Pytest configuration."""

from __future__ import annotations

import sys
from pathlib import Path
from types import MappingProxyType

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import GameState, SnakeState
from models import Position


@pytest.fixture
def make_state():
    """Create a GameState for testing with configurable parameters."""
    def _make(snakes, food=None, width=12, height=12, frame=0):
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
    return _make


@pytest.fixture
def snake():
    """Helper fixture to create a SnakeState for testing."""
    def _snake(id_: int, *segments: tuple[int, int], direction=None) -> SnakeState:
        from models import Direction
        
        if direction is None:
            direction = Direction.RIGHT
        
        body = tuple(Position(x, y) for x, y in segments)
        return SnakeState(id=id_, body=body, direction=direction)
    return _snake
