"""
Behaviour-focused tests for the GreedyAIController with personality strategies.
"""

from __future__ import annotations

from ai import GreedyAIController, SnakeStrategy, StrategyFactory
from config import AIConfig, AIPersonality
from engine import SnakeState
from models import Direction, Position


def build_controller(
    snakes: list[SnakeState],
    strategies: dict[int, SnakeStrategy] | None = None,
    ai_config: AIConfig | None = None,
) -> GreedyAIController:
    descriptor = strategies or {
        snake.id: SnakeStrategy(AIPersonality.BALANCED) for snake in snakes
    }
    return GreedyAIController(descriptor, ai_config or AIConfig(), StrategyFactory())


class TestGreedyAIController:
    def test_moves_toward_nearest_food(self, make_state) -> None:
        snake = SnakeState(
            id=0,
            body=(Position(4, 4),),
            direction=Direction.RIGHT,
        )
        state = make_state([snake], {Position(7, 4)})
        controller = build_controller([snake])

        decisions = controller.decide(state)

        assert decisions[0] == Direction.RIGHT

    def test_avoids_walls(self, make_state) -> None:
        snake = SnakeState(
            id=0,
            body=(Position(5, 1),),
            direction=Direction.UP,
        )
        state = make_state([snake], {Position(5, 0)})
        controller = build_controller([snake])

        decisions = controller.decide(state)

        assert decisions[0] != Direction.UP

    def test_prefers_open_space_without_food(self, make_state) -> None:
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

        assert decisions[0] in {Direction.UP, Direction.DOWN, Direction.LEFT}

    def test_handles_no_safe_moves(self, make_state) -> None:
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

    def test_aggressive_targets_opponent(self, make_state) -> None:
        aggressive = SnakeState(
            id=0,
            body=(Position(2, 2),),
            direction=Direction.RIGHT,
        )
        rival = SnakeState(
            id=1,
            body=(Position(5, 2), Position(6, 2)),
            direction=Direction.LEFT,
        )
        state = make_state([aggressive, rival], {Position(2, 1)})
        strategies = {
            0: SnakeStrategy(AIPersonality.AGGRESSIVE),
            1: SnakeStrategy(AIPersonality.DEFENSIVE),
        }
        controller = build_controller([aggressive, rival], strategies)

        decisions = controller.decide(state)

        assert decisions[0] == Direction.RIGHT

    def test_defensive_prefers_space_over_food(self, make_state) -> None:
        defender = SnakeState(
            id=0,
            body=(Position(4, 4),),
            direction=Direction.RIGHT,
        )
        rival = SnakeState(
            id=1,
            body=(Position(4, 2),),
            direction=Direction.DOWN,
        )
        state = make_state([defender, rival], {Position(4, 3)})
        strategies = {
            0: SnakeStrategy(AIPersonality.DEFENSIVE),
            1: SnakeStrategy(AIPersonality.AGGRESSIVE),
        }
        controller = build_controller([defender, rival], strategies)

        decisions = controller.decide(state)

        assert decisions[0] == Direction.DOWN

    def test_balanced_respects_max_path_length(self, make_state) -> None:
        snake = SnakeState(
            id=0,
            body=(Position(1, 1),),
            direction=Direction.RIGHT,
        )
        state = make_state([snake], {Position(4, 1)}, width=10, height=10)
        controller = build_controller(
            [snake],
            ai_config=AIConfig(MAX_PATH_LENGTH=0),
        )

        decisions = controller.decide(state)

        assert decisions[0] == Direction.DOWN

    def test_aggressive_falls_back_when_paths_exceed_limit(self, make_state) -> None:
        hunter = SnakeState(
            id=0,
            body=(Position(1, 1),),
            direction=Direction.RIGHT,
        )
        rival = SnakeState(
            id=1,
            body=(Position(6, 1),),
            direction=Direction.LEFT,
        )
        state = make_state([hunter, rival], width=10, height=10)
        strategies = {
            0: SnakeStrategy(AIPersonality.AGGRESSIVE),
            1: SnakeStrategy(AIPersonality.DEFENSIVE),
        }
        controller = build_controller(
            [hunter, rival],
            strategies=strategies,
            ai_config=AIConfig(MAX_PATH_LENGTH=0),
        )

        decisions = controller.decide(state)

        assert decisions[0] == Direction.DOWN
