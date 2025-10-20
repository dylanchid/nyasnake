"""
Strategy-aware AI controller implementation for Nyasnake.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Protocol, Sequence, Tuple

from config import AIConfig, AIPersonality
from engine import GameState, SnakeState
from models import Direction, Position
from pathfinding import find_path


@dataclass(frozen=True)
class SnakeStrategy:
    """Descriptor that selects a behaviour strategy for a snake."""

    personality: AIPersonality


@dataclass(frozen=True)
class StrategyContext:
    """Immutable bundle of data required for strategy evaluation."""

    state: GameState
    snake: SnakeState
    ai_config: AIConfig


class SnakeBehaviorStrategy(Protocol):
    """Strategy interface returning a desired direction for the given context."""

    def choose_direction(self, context: StrategyContext) -> Direction:
        ...


class BalancedStrategy(SnakeBehaviorStrategy):
    """Default behaviour – pursue food, otherwise keep to open space."""

    def choose_direction(self, context: StrategyContext) -> Direction:
        state = context.state
        snake = context.snake

        safe_directions = _safe_directions(state, snake)
        if not safe_directions:
            safe_directions = _permissive_directions(state, snake)
            if not safe_directions:
                return snake.direction

        target_food = _nearest_food(state, snake.head())
        if target_food is not None:
            direction = _choose_toward_target(
                state,
                snake,
                safe_directions,
                target_food,
                context.ai_config,
            )
            if direction is not None:
                return direction

        return max(
            safe_directions,
            key=lambda direction: _available_space(state, snake, direction, context.ai_config),
        )


class AggressiveStrategy(BalancedStrategy):
    """Hunts opponents when advantageous, otherwise defers to balanced play."""

    def choose_direction(self, context: StrategyContext) -> Direction:
        state = context.state
        snake = context.snake

        safe_directions = _safe_directions(state, snake)
        if not safe_directions:
            safe_directions = _permissive_directions(state, snake)
            if not safe_directions:
                return snake.direction

        target_snake = _nearest_rival(state, snake)
        if target_snake is not None:
            direction = _choose_toward_target(
                state,
                snake,
                safe_directions,
                target_snake.head(),
                context.ai_config,
            )
            if direction is not None:
                return direction

        return super().choose_direction(context)


class DefensiveStrategy(BalancedStrategy):
    """Prioritises safe space and distance from opponents."""

    def choose_direction(self, context: StrategyContext) -> Direction:
        state = context.state
        snake = context.snake

        safe_directions = _safe_directions(state, snake)
        if not safe_directions:
            safe_directions = _permissive_directions(state, snake)
            if not safe_directions:
                return snake.direction

        best_direction: Optional[Direction] = None
        best_score = float("-inf")
        for direction in safe_directions:
            next_head = snake.head() + direction
            space = _available_space(state, snake, direction, context.ai_config)
            distance = _distance_to_nearest_enemy(state, snake, next_head)
            score = (space * 2) + distance
            if score > best_score:
                best_score = score
                best_direction = direction

        if best_direction is not None:
            return best_direction

        return super().choose_direction(context)


class StrategyFactory:
    """Factory that maps personalities to concrete strategy objects."""

    def __init__(self) -> None:
        self._strategies: Dict[AIPersonality, SnakeBehaviorStrategy] = {
            AIPersonality.BALANCED: BalancedStrategy(),
            AIPersonality.AGGRESSIVE: AggressiveStrategy(),
            AIPersonality.DEFENSIVE: DefensiveStrategy(),
        }

    def create(self, personality: AIPersonality) -> SnakeBehaviorStrategy:
        return self._strategies.get(personality, self._strategies[AIPersonality.BALANCED])


class GreedyAIController:
    """
    Produces synchronous decisions for each alive snake using configurable strategies.
    """

    def __init__(
        self,
        strategies: Mapping[int, SnakeStrategy],
        ai_config: AIConfig,
        strategy_factory: Optional[StrategyFactory] = None,
    ):
        self._strategies = dict(strategies)
        self._ai_config = ai_config
        self._strategy_factory = strategy_factory or StrategyFactory()

    def decide(self, state: GameState) -> Dict[int, Direction]:
        decisions: Dict[int, Direction] = {}
        for snake in state.snakes:
            if not snake.alive:
                continue
            decisions[snake.id] = self._decide_for_snake(state, snake)
        return decisions

    def _decide_for_snake(self, state: GameState, snake: SnakeState) -> Direction:
        descriptor = self._strategies.get(snake.id)
        personality = descriptor.personality if descriptor else AIPersonality.BALANCED
        strategy = self._strategy_factory.create(personality)
        context = StrategyContext(state=state, snake=snake, ai_config=self._ai_config)
        return strategy.choose_direction(context)


def _choose_toward_target(
    state: GameState,
    snake: SnakeState,
    options: Sequence[Direction],
    target: Position,
    ai_config: AIConfig,
) -> Optional[Direction]:
    best_direction: Optional[Direction] = None
    best_score: Optional[Tuple[int, int]] = None
    head = snake.head()

    for direction in options:
        next_head = head + direction
        path = find_path(state, snake.id, next_head, target)
        if path is None:
            current_distance = head.distance_to(target)
            next_distance = next_head.distance_to(target)
            if next_distance >= current_distance:
                continue
            candidate = (1, next_distance)
        else:
            if len(path) > ai_config.MAX_PATH_LENGTH:
                continue
            candidate = (0, len(path))

        if best_score is None or candidate < best_score:
            best_score = candidate
            best_direction = direction

    return best_direction


def _safe_directions(state: GameState, snake: SnakeState) -> list[Direction]:
    head = snake.head()
    safe: list[Direction] = []
    for direction in Direction:
        if snake.length() > 1 and direction == snake.direction.opposite():
            continue
        candidate = head + direction
        if not state.is_within_bounds(candidate):
            continue
        if _is_cell_safe(state, snake, candidate):
            safe.append(direction)
    return safe


def _permissive_directions(state: GameState, snake: SnakeState) -> list[Direction]:
    head = snake.head()
    options: list[Direction] = []
    for direction in Direction:
        candidate = head + direction
        if not state.is_within_bounds(candidate):
            continue
        if _is_cell_safe(state, snake, candidate, allow_tail=False):
            options.append(direction)
    return options


def _nearest_food(state: GameState, head: Position) -> Optional[Position]:
    if not state.food:
        return None
    return min(state.food, key=lambda food: head.distance_to(food))


def _nearest_rival(state: GameState, snake: SnakeState) -> Optional[SnakeState]:
    opponents = [
        other
        for other in state.snakes
        if other.alive and other.id != snake.id
    ]
    if not opponents:
        return None
    head = snake.head()
    return min(opponents, key=lambda other: head.distance_to(other.head()))


def _distance_to_nearest_enemy(state: GameState, snake: SnakeState, position: Position) -> int:
    distances = [
        position.distance_to(other.head())
        for other in state.snakes
        if other.alive and other.id != snake.id
    ]
    if not distances:
        return position.distance_to(snake.head())
    return min(distances)


def _available_space(
    state: GameState,
    snake: SnakeState,
    direction: Direction,
    ai_config: AIConfig,
) -> int:
    from collections import deque

    head = snake.head() + direction
    frontier = deque([head])
    visited = {pos for pos in snake.body}
    visited.add(head)

    while frontier and len(visited) < ai_config.SPACE_SEARCH_LIMIT:
        current = frontier.popleft()
        for neighbor in current.neighbors():
            if neighbor in visited:
                continue
            if not state.is_within_bounds(neighbor):
                continue
            if not _is_cell_safe(state, snake, neighbor):
                continue
            visited.add(neighbor)
            frontier.append(neighbor)

    return len(visited)


def _is_cell_safe(
    state: GameState,
    snake: SnakeState,
    pos: Position,
    allow_tail: bool = True,
) -> bool:
    occupant = state.occupied.get(pos)
    if occupant is None:
        return True
    if occupant != snake.id:
        return False
    if not allow_tail:
        return False
    return bool(snake.body) and pos == snake.body[-1]
