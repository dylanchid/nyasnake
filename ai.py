"""
Simplified AI controller that supports greedy food seeking with A* fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional

from config import AIPersonality
from engine import GameState, SnakeState
from models import Direction, Position
from pathfinding import find_path


@dataclass(frozen=True)
class SnakeStrategy:
    """Light-weight strategy descriptor mapping personalities to behaviors."""

    personality: AIPersonality


class GreedyAIController:
    """
    Produces synchronous decisions for each alive snake using a greedy heuristic.
    Prioritises food via A* and falls back to the safest available move.
    """

    def __init__(self, strategies: Mapping[int, SnakeStrategy]):
        self._strategies = dict(strategies)

    def decide(self, state: GameState) -> Dict[int, Direction]:
        decisions: Dict[int, Direction] = {}
        for snake in state.snakes:
            if not snake.alive:
                continue
            decision = self._decide_for_snake(state, snake)
            if decision is not None:
                decisions[snake.id] = decision
        return decisions

    def _decide_for_snake(self, state: GameState, snake: SnakeState) -> Optional[Direction]:
        safe_directions = _safe_directions(state, snake)
        if not safe_directions:
            # Allow reversing if it's the only way to move
            safe_directions = _permissive_directions(state, snake)
            if not safe_directions:
                return snake.direction

        target_food = _nearest_food(state, snake.head())
        if target_food is not None:
            direction = self._choose_toward_target(state, snake, safe_directions, target_food)
            if direction is not None:
                return direction

        # Fallback: pick direction with the most free neighbors
        return max(
            safe_directions,
            key=lambda d: _available_space(state, snake, d),
        )

    def _choose_toward_target(
        self,
        state: GameState,
        snake: SnakeState,
        options: Iterable[Direction],
        target: Position,
    ) -> Optional[Direction]:
        best_direction = None
        best_score = float("inf")
        head = snake.head()

        for direction in options:
            next_head = head + direction
            path = find_path(state, snake.id, next_head, target)
            if path is None:
                # Prefer options that at least reduce the Manhattan distance
                score = head.distance_to(target)
                if next_head.distance_to(target) < score and score < best_score:
                    best_direction = direction
                    best_score = score
                continue

            score = len(path)
            if score < best_score:
                best_score = score
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


def _is_cell_safe(state: GameState, snake: SnakeState, pos: Position, allow_tail: bool = True) -> bool:
    occupant = state.occupied.get(pos)
    if occupant is None:
        return True
    if occupant != snake.id:
        return False
    if not allow_tail:
        return False
    return snake.body and pos == snake.body[-1]


def _nearest_food(state: GameState, head: Position) -> Optional[Position]:
    if not state.food:
        return None
    return min(state.food, key=lambda food: head.distance_to(food))


def _available_space(state: GameState, snake: SnakeState, direction: Direction) -> int:
    head = snake.head() + direction
    frontier = [head]
    visited = {pos for pos in snake.body}
    visited.add(head)
    count = 0

    while frontier and count < 15:
        current = frontier.pop()
        count += 1
        for neighbor in current.neighbors():
            if neighbor in visited:
                continue
            if not state.is_within_bounds(neighbor):
                continue
            if not _is_cell_safe(state, snake, neighbor):
                continue
            visited.add(neighbor)
            frontier.append(neighbor)
    return count
