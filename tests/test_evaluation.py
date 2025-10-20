"""
Engine-level tests covering movement, scoring, and collisions.
"""

from __future__ import annotations

from random import Random

from engine import GameState, SnakeState, advance_state
from models import Direction, Position


class TestAdvanceState:
    def test_food_consumption_adds_score_and_respawns(self, make_state) -> None:
        snake = SnakeState(
            id=0,
            body=(Position(3, 3),),
            direction=Direction.RIGHT,
        )
        food = {Position(4, 3)}
        state = make_state([snake], food)
        rng = Random(42)

        result = advance_state(state, {0: Direction.RIGHT}, rng, desired_food=1)

        updated = next(s for s in result.state.snakes if s.id == 0)
        assert updated.score == 10
        assert len(result.state.food) == 1
        assert Position(4, 3) not in result.state.food
        assert len(updated.body) == 2

    def test_wall_collision_marks_snake_dead(self, make_state) -> None:
        snake = SnakeState(
            id=0,
            body=(Position(1, 1),),
            direction=Direction.LEFT,
        )
        state = make_state([snake])
        rng = Random(0)

        result = advance_state(state, {0: Direction.LEFT}, rng, desired_food=0)

        updated = next(s for s in result.state.snakes if s.id == 0)
        assert not updated.alive

    def test_longer_snake_wins_head_to_head(self, make_state) -> None:
        long_snake = SnakeState(
            id=0,
            body=(Position(4, 4), Position(3, 4), Position(2, 4)),
            direction=Direction.RIGHT,
        )
        short_snake = SnakeState(
            id=1,
            body=(Position(6, 4), Position(7, 4)),
            direction=Direction.LEFT,
        )
        state = make_state([long_snake, short_snake])
        rng = Random(0)

        result = advance_state(
            state,
            {0: Direction.RIGHT, 1: Direction.LEFT},
            rng,
            desired_food=0,
        )

        snakes = {s.id: s for s in result.state.snakes}
        assert snakes[0].alive
        assert not snakes[1].alive
        assert snakes[0].kills == 1

    def test_equal_length_head_to_head_eliminates_both(self, make_state) -> None:
        snake_a = SnakeState(
            id=0,
            body=(Position(4, 4), Position(3, 4)),
            direction=Direction.RIGHT,
        )
        snake_b = SnakeState(
            id=1,
            body=(Position(6, 4), Position(7, 4)),
            direction=Direction.LEFT,
        )
        state = make_state([snake_a, snake_b])
        rng = Random(1)

        result = advance_state(
            state,
            {0: Direction.RIGHT, 1: Direction.LEFT},
            rng,
            desired_food=0,
        )

        snakes = {s.id: s for s in result.state.snakes}
        assert not snakes[0].alive
        assert not snakes[1].alive
        assert snakes[0].kills == snakes[1].kills == 0

    def test_food_respawn_maintains_target_count(self, make_state) -> None:
        snake = SnakeState(
            id=0,
            body=(Position(3, 3),),
            direction=Direction.RIGHT,
        )
        foods = {Position(4, 3), Position(5, 5)}
        state = make_state([snake], foods)
        rng = Random(2)

        result = advance_state(state, {0: Direction.RIGHT}, rng, desired_food=3)

        assert len(result.state.food) == 3
        updated = next(s for s in result.state.snakes if s.id == 0)
        assert updated.score == 10
