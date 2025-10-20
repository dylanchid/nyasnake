"""
Core geometric primitives used by the Nyasnake engine and AI.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Tuple


class Direction(Enum):
    """Cardinal directions with unit vector offsets."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    def opposite(self) -> "Direction":
        mapping = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }
        return mapping[self]

    @property
    def delta(self) -> Tuple[int, int]:
        return self.value


@dataclass(frozen=True)
class Position:
    """Immutable 2D grid position."""

    x: int
    y: int

    def __add__(self, direction: Direction) -> "Position":
        dx, dy = direction.delta
        return Position(self.x + dx, self.y + dy)

    def distance_to(self, other: "Position") -> int:
        """Manhattan distance."""
        return abs(self.x - other.x) + abs(self.y - other.y)

    def neighbors(self) -> Iterable["Position"]:
        for direction in Direction:
            yield self + direction

    def __hash__(self) -> int:
        return hash((self.x, self.y))
