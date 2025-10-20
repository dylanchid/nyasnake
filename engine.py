"""
Pure game engine for Nyasnake.
Provides immutable state structures and deterministic tick transitions.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple
from types import MappingProxyType
from random import Random

from models import Direction, Position


@dataclass(frozen=True)
class SnakeState:
    """Immutable snake state used by the engine."""

    id: int
    body: Tuple[Position, ...]
    direction: Direction
    alive: bool = True
    score: int = 0
    kills: int = 0

    def head(self) -> Position:
        return self.body[0]

    def length(self) -> int:
        return len(self.body)


@dataclass(frozen=True)
class GameState:
    """Immutable snapshot of the board."""

    snakes: Tuple[SnakeState, ...]
    food: frozenset
    occupied: Mapping[Position, int]
    width: int
    height: int
    frame: int = 0

    def is_within_bounds(self, pos: Position) -> bool:
        return 0 < pos.x < self.width - 1 and 0 < pos.y < self.height - 1

    def is_occupied(self, pos: Position) -> bool:
        return pos in self.occupied

    def find_snake(self, snake_id: int) -> Optional[SnakeState]:
        return next((s for s in self.snakes if s.id == snake_id), None)


@dataclass(frozen=True)
class SnakeSpawn:
    """Spawn definition for a snake."""

    id: int
    body: Tuple[Position, ...]
    direction: Direction


@dataclass(frozen=True)
class GameEvent:
    """Event emitted during a tick."""

    type: str
    snake_id: Optional[int] = None
    position: Optional[Position] = None
    payload: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TickResult:
    """Result of advancing the engine one frame."""

    state: GameState
    events: Tuple[GameEvent, ...]


def _build_occupancy(snakes: Iterable[SnakeState]) -> Mapping[Position, int]:
    occupied: Dict[Position, int] = {}
    for snake in snakes:
        if not snake.alive:
            continue
        for segment in snake.body:
            occupied[segment] = snake.id
    return MappingProxyType(occupied)


def create_initial_state(
    width: int,
    height: int,
    spawns: Sequence[SnakeSpawn],
    initial_food: int,
    rng: Random,
) -> GameState:
    """Create the starting state for a match."""
    snakes = tuple(
        SnakeState(id=spawn.id, body=spawn.body, direction=spawn.direction)
        for spawn in spawns
    )
    food = _spawn_food(width, height, snakes, frozenset(), initial_food, rng)
    occupied = _build_occupancy(snakes)
    return GameState(snakes=snakes, food=food, occupied=occupied, width=width, height=height)


def advance_state(
    state: GameState,
    decisions: Mapping[int, Direction],
    rng: Random,
    desired_food: int,
) -> TickResult:
    """
    Advance the game by one frame.

    Decisions map snake id to desired direction. If a decision is the direct
    opposite of the current direction it is ignored.
    """
    moved = []
    food = set(state.food)
    generated_events: list[GameEvent] = []

    for snake in state.snakes:
        if not snake.alive:
            moved.append(
                snake  # dead snakes persist as corpses but removed from occupancy later
            )
            continue

        direction = decisions.get(snake.id, snake.direction)
        if direction == snake.direction.opposite():
            direction = snake.direction

        body_deque = deque(snake.body)
        new_head = snake.head() + direction
        body_deque.appendleft(new_head)

        ate_food = new_head in food
        if not ate_food:
            body_deque.pop()
        else:
            food.remove(new_head)
            generated_events.append(
                GameEvent(type="food_consumed", snake_id=snake.id, position=new_head)
            )

        moved.append(
            SnakeState(
                id=snake.id,
                body=tuple(body_deque),
                direction=direction,
                score=snake.score + (10 if ate_food else 0),
                kills=snake.kills,
                alive=True,
            )
        )

    # Collision phase
    alive_flags: Dict[int, bool] = {snake.id: snake.alive for snake in moved}
    lengths: Dict[int, int] = {snake.id: snake.length() for snake in moved}

    # Wall / self collisions
    for snake in moved:
        if not snake.alive:
            alive_flags[snake.id] = False
            continue
        head = snake.head()
        if not _is_within_bounds(head, state.width, state.height):
            alive_flags[snake.id] = False
            generated_events.append(
                GameEvent(type="snake_died", snake_id=snake.id, position=head)
            )
            continue
        if head in snake.body[1:]:
            alive_flags[snake.id] = False
            generated_events.append(
                GameEvent(type="snake_died", snake_id=snake.id, position=head)
            )

    # Head-to-head collisions
    head_positions: Dict[Position, list] = {}
    for snake in moved:
        if not alive_flags.get(snake.id, False):
            continue
        head_positions.setdefault(snake.head(), []).append(snake.id)

    for position, contenders in head_positions.items():
        if len(contenders) <= 1:
            continue
        best_length = max(lengths[snake_id] for snake_id in contenders)
        survivors = [
            snake_id
            for snake_id in contenders
            if lengths[snake_id] == best_length
        ]
        if len(survivors) == 1:
            winner = survivors[0]
            win_count = 0
            for snake_id in contenders:
                if snake_id == winner:
                    continue
                if alive_flags.get(snake_id, False):
                    alive_flags[snake_id] = False
                    win_count += 1
                    generated_events.append(
                        GameEvent(type="snake_died", snake_id=snake_id, position=position)
                    )
            if win_count > 0:
                _award_kill(moved, winner, win_count)
        else:
            for snake_id in contenders:
                if alive_flags.get(snake_id, False):
                    alive_flags[snake_id] = False
                    generated_events.append(
                        GameEvent(type="snake_died", snake_id=snake_id, position=position)
                    )

    # Head into another body
    body_positions: Dict[Position, int] = {}
    for snake in moved:
        if not alive_flags.get(snake.id, False):
            continue
        for segment in snake.body[1:]:
            body_positions.setdefault(segment, snake.id)

    for snake in moved:
        if not alive_flags.get(snake.id, False):
            continue
        head = snake.head()
        occupant = body_positions.get(head)
        if occupant is not None and occupant != snake.id:
            alive_flags[snake.id] = False
            generated_events.append(
                GameEvent(type="snake_died", snake_id=snake.id, position=head)
            )
            _award_kill(moved, occupant, 1)

    # Apply death flags to moved snakes
    next_snakes = []
    for snake in moved:
        is_alive = alive_flags.get(snake.id, False) and snake.alive
        if not is_alive:
            next_snakes.append(
                SnakeState(
                    id=snake.id,
                    body=snake.body,
                    direction=snake.direction,
                    alive=False,
                    score=snake.score,
                    kills=snake.kills,
                )
            )
        else:
            next_snakes.append(snake)

    alive_snakes = tuple(s for s in next_snakes if s.alive)

    # Respawn food if needed
    if len(food) < desired_food:
        food = _spawn_food(
            state.width,
            state.height,
            alive_snakes,
            frozenset(food),
            desired_food - len(food),
            rng,
        )
    else:
        food = frozenset(food)

    occupied = _build_occupancy(alive_snakes)
    next_state = GameState(
        snakes=next_snakes,
        food=food,
        occupied=occupied,
        width=state.width,
        height=state.height,
        frame=state.frame + 1,
    )
    events = tuple(generated_events)
    return TickResult(state=next_state, events=events)


def _spawn_food(
    width: int,
    height: int,
    snakes: Sequence[SnakeState],
    existing_food: frozenset,
    count: int,
    rng: Random,
) -> frozenset:
    """Spawn additional food items in free cells."""
    occupied = {seg for snake in snakes for seg in snake.body}
    occupied.update(existing_food)
    available = [
        Position(x, y)
        for x in range(1, width - 1)
        for y in range(1, height - 1)
        if Position(x, y) not in occupied
    ]
    rng.shuffle(available)
    new_food = list(existing_food)
    for _ in range(count):
        if not available:
            break
        new_food.append(available.pop())
    return frozenset(new_food)


def _is_within_bounds(pos: Position, width: int, height: int) -> bool:
    return 0 < pos.x < width - 1 and 0 < pos.y < height - 1


def _award_kill(snakes: Sequence[SnakeState], killer_id: int, kills: int) -> None:
    for index, snake in enumerate(snakes):
        if snake.id == killer_id:
            snakes[index] = SnakeState(
                id=snake.id,
                body=snake.body,
                direction=snake.direction,
                alive=snake.alive,
                score=snake.score,
                kills=snake.kills + kills,
            )
            break
