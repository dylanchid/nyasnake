"""
Behaviour-focused tests for the GreedyAIController.
"""

from __future__ import annotations

from types import MappingProxyType

from ai import GreedyAIController, SnakeStrategy
from config import AIPersonality
from engine import GameState, SnakeState
from models import Direction, Position


def make_state(
    snakes: list[SnakeState],
    food: set[Position] | None = None,
    width: int = 12,
    height: int = 12,
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
    )


def build_controller(snakes: list[SnakeState]) -> GreedyAIController:
    strategies = {
        snake.id: SnakeStrategy(AIPersonality.BALANCED) for snake in snakes
    }
    return GreedyAIController(strategies)


class TestGreedyAIController:
    def test_moves_toward_nearest_food(self) -> None:
        snake = SnakeState(
            id=0,
            body=(Position(4, 4),),
            direction=Direction.RIGHT,
        )
        state = make_state([snake], {Position(7, 4)})
        controller = build_controller([snake])

        decisions = controller.decide(state)

        assert decisions[0] == Direction.RIGHT

    def test_avoids_walls(self) -> None:
        snake = SnakeState(
            id=0,
            body=(Position(5, 1),),
            direction=Direction.UP,
        )
        state = make_state([snake], {Position(5, 0)})
        controller = build_controller([snake])

        decisions = controller.decide(state)

        assert decisions[0] != Direction.UP

    def test_prefers_open_space_without_food(self) -> None:
        snake = SnakeState(
            id=0,
            body=(Position(5, 5),),
            direction=Direction.RIGHT,
        )
        blocker = SnakeState(
            id=1,
            body=(
                Position(6, 5),
                Position(7, 5),
                Position(7, 6),
            ),
            direction=Direction.LEFT,
        )
        state = make_state([snake, blocker])
        controller = build_controller([snake, blocker])

        decisions = controller.decide(state)

        assert decisions[0] in {Direction.UP, Direction.DOWN}

    def test_handles_no_safe_moves(self) -> None:
        snake = SnakeState(
            id=0,
            body=(Position(3, 3), Position(3, 4), Position(2, 3), Position(2, 4)),
            direction=Direction.RIGHT,
        )
        walls = SnakeState(
            id=1,
            body=(Position(4, 3), Position(4, 2), Position(3, 2), Position(2, 2)),
            direction=Direction.LEFT,
        )
        state = make_state([snake, walls])
        controller = build_controller([snake, walls])

        decisions = controller.decide(state)

        assert decisions[0] in Direction
