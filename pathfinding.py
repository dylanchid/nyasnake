"""
Lightweight pathfinding utilities operating on immutable game state snapshots.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Set, Tuple

from engine import GameState
from models import Direction, Position


def find_path(
    state: GameState,
    snake_id: int,
    start: Position,
    goal: Position,
) -> Optional[List[Position]]:
    """
    Compute a simple A* path from start to goal avoiding occupied cells.
    Returns a list of positions (excluding start) or None if unreachable.
    """
    if start == goal:
        return []

    open_heap: List[Tuple[int, int, int, Position]] = []
    counter = 0
    heapq.heappush(open_heap, (_heuristic(start, goal), counter, 0, start))

    came_from: Dict[Position, Position] = {}
    g_score: Dict[Position, int] = {start: 0}
    visited: Set[Position] = set()

    while open_heap:
        _, _, distance, current = heapq.heappop(open_heap)
        if current in visited:
            continue
        visited.add(current)

        if current == goal:
            return _reconstruct_path(came_from, current)

        for neighbor in _neighbors(state, snake_id, current, goal):
            tentative = distance + 1
            if tentative < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative
                priority = tentative + _heuristic(neighbor, goal)
                counter += 1
                heapq.heappush(open_heap, (priority, counter, tentative, neighbor))

    return None


def _heuristic(pos: Position, goal: Position) -> int:
    return pos.distance_to(goal)


def _neighbors(
    state: GameState, snake_id: int, pos: Position, goal: Position
) -> List[Position]:
    neighbors = []
    for direction in Direction:
        candidate = pos + direction
        if not state.is_within_bounds(candidate):
            continue
        if _is_walkable(state, snake_id, candidate, goal):
            neighbors.append(candidate)
    return neighbors


def _is_walkable(
    state: GameState, snake_id: int, pos: Position, goal: Position
) -> bool:
    if pos == goal:
        return True
    occupant = state.occupied.get(pos)
    if occupant is None:
        return True
    if occupant == snake_id:
        snake = state.find_snake(snake_id)
        if snake and snake.body and pos == snake.body[-1]:
            return True
    return False


def _reconstruct_path(came_from: Dict[Position, Position], current: Position) -> List[Position]:
    path = []
    while current in came_from:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path
