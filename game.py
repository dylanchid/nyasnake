"""
Synchronous game runner with a phase-based loop and pluggable renderer/input.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass
from random import Random
from typing import Dict, Mapping, Optional, Protocol, Sequence

from ai import GreedyAIController, SnakeStrategy
from config import AIPersonality, DEBUG_CONFIG, DISPLAY_CONFIG, GAME_CONFIG
from engine import GameEvent, GameState, SnakeSpawn, advance_state, create_initial_state
from models import Direction, Position

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SnakeProfile:
    """Visual and behavioral metadata for a snake id."""

    id: int
    personality: AIPersonality
    color: str
    symbol: str


class DecisionProvider(Protocol):
    """Callable that produces direction choices for all alive snakes."""

    def decide(self, state: GameState) -> Mapping[int, Direction]:
        ...


class InputProvider:
    """Base class for user input providers."""

    def poll(self) -> Dict[int, Direction]:
        """
        Collect decisions for controllable snakes.
        Default implementation returns no overrides.
        """
        return {}

    def close(self) -> None:
        """Hook for releasing terminal resources."""
        return


class KeyboardInput(InputProvider):
    """
    Cross-platform non-blocking keyboard input provider.
    Key bindings map lowercase characters to (snake_id, Direction) tuples.
    """

    def __init__(self, bindings: Mapping[str, tuple[int, Direction]]):
        self._bindings = {key.lower(): value for key, value in bindings.items()}
        self._is_windows = os.name == "nt"
        self._fd: Optional[int] = None
        self._tty_attrs = None
        if not self._is_windows:
            import termios
            import tty

            self._fd = sys.stdin.fileno()
            self._tty_attrs = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)

    def poll(self) -> Dict[int, Direction]:
        decisions: Dict[int, Direction] = {}
        if self._is_windows:
            decisions.update(self._poll_windows())
        else:
            decisions.update(self._poll_posix())
        return decisions

    def close(self) -> None:
        if not self._is_windows and self._fd is not None and self._tty_attrs is not None:
            import termios

            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._tty_attrs)
        self._tty_attrs = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            # Avoid raising during interpreter shutdown
            pass

    def _poll_windows(self) -> Dict[int, Direction]:
        decisions: Dict[int, Direction] = {}
        try:
            import msvcrt  # type: ignore
        except ImportError:
            return decisions

        while msvcrt.kbhit():
            char = msvcrt.getwch()
            if not char:
                continue
            mapping = self._bindings.get(char.lower())
            if mapping:
                snake_id, direction = mapping
                decisions[snake_id] = direction
        return decisions

    def _poll_posix(self) -> Dict[int, Direction]:
        decisions: Dict[int, Direction] = {}
        import select

        while True:
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if not ready:
                break
            char = sys.stdin.read(1)
            if not char:
                break
            mapping = self._bindings.get(char.lower())
            if mapping:
                snake_id, direction = mapping
                decisions[snake_id] = direction
        return decisions


class Renderer:
    """Base class for rendering game state."""

    def render(
        self,
        state: GameState,
        profiles: Mapping[int, SnakeProfile],
        events: Sequence[GameEvent],
        debug_enabled: bool,
    ) -> None:
        raise NotImplementedError


class AnsiRenderer(Renderer):
    """ANSI terminal renderer used as the default fallback backend."""

    def render(
        self,
        state: GameState,
        profiles: Mapping[int, SnakeProfile],
        events: Sequence[GameEvent],
        debug_enabled: bool,
    ) -> None:
        print("\033[2J\033[H", end="")  # clear screen

        grid = [[" " for _ in range(state.width)] for _ in range(state.height)]
        self._draw_border(grid, state.width, state.height)
        self._draw_food(grid, state)
        self._draw_snakes(grid, state, profiles)

        for row in grid:
            print("".join(row))

        print("\n" + "=" * state.width)
        self._print_status(state, profiles)
        if events and DEBUG_CONFIG.LOG_DECISIONS:
            for event in events:
                print(f"  • Event: {event.type} (snake={event.snake_id}, pos={event.position})")

        if debug_enabled:
            print(f"Debug Mode: danger_zones={DEBUG_CONFIG.SHOW_DANGER_ZONES}, paths={DEBUG_CONFIG.SHOW_PATHS}")

        alive_count = sum(1 for snake in state.snakes if snake.alive)
        if alive_count <= 1:
            print("\n" + "=" * state.width)
            if alive_count == 1:
                winner = next(s for s in state.snakes if s.alive)
                profile = profiles[winner.id]
                name = profile.personality.name
                print(f"🏆 {name} Snake Wins!")
            else:
                print("All snakes eliminated!")

        print(f"\nFrame: {state.frame}/{GAME_CONFIG.MAX_ROUNDS}")

    def _draw_border(self, grid: list[list[str]], width: int, height: int) -> None:
        symbols = DISPLAY_CONFIG.SYMBOLS
        for x in range(width):
            grid[0][x] = symbols["border_h"]
            grid[height - 1][x] = symbols["border_h"]
        for y in range(height):
            grid[y][0] = symbols["border_v"]
            grid[y][width - 1] = symbols["border_v"]
        grid[0][0] = symbols["corner_tl"]
        grid[0][width - 1] = symbols["corner_tr"]
        grid[height - 1][0] = symbols["corner_bl"]
        grid[height - 1][width - 1] = symbols["corner_br"]

    def _draw_food(self, grid: list[list[str]], state: GameState) -> None:
        for food_pos in state.food:
            if 0 <= food_pos.y < state.height and 0 <= food_pos.x < state.width:
                grid[food_pos.y][food_pos.x] = (
                    f"{DISPLAY_CONFIG.COLORS['yellow']}"
                    f"{DISPLAY_CONFIG.SYMBOLS['food']}"
                    f"{DISPLAY_CONFIG.COLORS['reset']}"
                )

    def _draw_snakes(
        self,
        grid: list[list[str]],
        state: GameState,
        profiles: Mapping[int, SnakeProfile],
    ) -> None:
        body_symbol = DISPLAY_CONFIG.SYMBOLS["snake_body"]
        for snake in state.snakes:
            profile = profiles.get(snake.id)
            if not profile:
                continue
            color = profile.color if snake.alive else DISPLAY_CONFIG.COLORS["gray"]
            for index, segment in enumerate(snake.body):
                if not (0 <= segment.x < state.width and 0 <= segment.y < state.height):
                    continue
                symbol = profile.symbol if index == 0 else body_symbol
                grid[segment.y][segment.x] = f"{color}{symbol}{DISPLAY_CONFIG.COLORS['reset']}"

    def _print_status(self, state: GameState, profiles: Mapping[int, SnakeProfile]) -> None:
        for snake in state.snakes:
            profile = profiles.get(snake.id)
            if not profile:
                continue
            status = "ALIVE" if snake.alive else "DEAD"
            color = profile.color if snake.alive else DISPLAY_CONFIG.COLORS["gray"]
            personality_name = profile.personality.name
            print(
                f"{color}{personality_name:11} Snake: {status:5} | "
                f"Score: {snake.score:4} | Length: {snake.length():3} | "
                f"Kills: {snake.kills}{DISPLAY_CONFIG.COLORS['reset']}"
            )


class GameRunner:
    """Coordinates the game loop and orchestrates phases."""

    def __init__(
        self,
        profiles: Sequence[SnakeProfile],
        renderer: Optional[Renderer] = None,
        input_provider: Optional[InputProvider] = None,
        rng: Optional[Random] = None,
        seed: Optional[int] = None,
        tick_interval: Optional[float] = None,
        ai_controller: Optional[DecisionProvider] = None,
    ):
        self._profiles = {profile.id: profile for profile in profiles}
        self._renderer = renderer or AnsiRenderer()
        self._input = input_provider or InputProvider()
        if rng is not None:
            self._rng = rng
            self._seed = None
        else:
            seed_value = seed if seed is not None else GAME_CONFIG.DEFAULT_SEED
            self._rng = Random(seed_value)
            self._seed = seed_value
        self._tick_interval = tick_interval if tick_interval is not None else GAME_CONFIG.TICK_INTERVAL
        self._desired_food = GAME_CONFIG.INITIAL_FOOD_COUNT
        self._max_rounds = GAME_CONFIG.MAX_ROUNDS
        self._state = create_initial_state(
            GAME_CONFIG.WIDTH,
            GAME_CONFIG.HEIGHT,
            self._default_spawns(),
            GAME_CONFIG.INITIAL_FOOD_COUNT,
            self._rng,
        )
        self._game_over = False
        strategies = {
            profile.id: SnakeStrategy(profile.personality) for profile in profiles
        }
        self._ai: DecisionProvider = ai_controller or GreedyAIController(strategies)

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def seed(self) -> Optional[int]:
        return self._seed

    @property
    def profiles(self) -> Mapping[int, SnakeProfile]:
        return self._profiles

    def run(self) -> None:
        """Run until completion or interruption."""
        debug_enabled = DEBUG_CONFIG.SHOW_DANGER_ZONES or DEBUG_CONFIG.SHOW_PATHS
        try:
            while not self._game_over and self._state.frame < self._max_rounds:
                frame_start = time.perf_counter()
                decisions = self._collect_decisions()
                tick = advance_state(self._state, decisions, self._rng, self._desired_food)
                self._apply_tick(tick, debug_enabled)
                self._game_over = self._evaluate_game_over()
                self._sleep_until_next_frame(frame_start)
        finally:
            self._renderer.render(self._state, self._profiles, (), debug_enabled)
            self._input.close()

    def _collect_decisions(self) -> Dict[int, Direction]:
        automated = dict(self._ai.decide(self._state))
        manual = self._input.poll()
        automated.update(manual)
        return automated

    def _apply_tick(self, tick: TickResult, debug_enabled: bool) -> None:
        self._state = tick.state
        self._renderer.render(tick.state, self._profiles, tick.events, debug_enabled)

    def _sleep_until_next_frame(self, frame_start: float) -> None:
        elapsed = time.perf_counter() - frame_start
        remaining = self._tick_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _evaluate_game_over(self) -> bool:
        alive = [snake for snake in self._state.snakes if snake.alive]
        if len(alive) <= 1:
            logger.info("Game over due to remaining snakes <= 1")
            return True
        return False

    def _default_spawns(self) -> Sequence[SnakeSpawn]:
        """Initial spawn configuration for the default three snakes."""
        return (
            SnakeSpawn(
                id=0,
                body=(Position(10, 10),),
                direction=Direction.RIGHT,
            ),
            SnakeSpawn(
                id=1,
                body=(Position(GAME_CONFIG.WIDTH - 10, 10),),
                direction=Direction.LEFT,
            ),
            SnakeSpawn(
                id=2,
                body=(Position(GAME_CONFIG.WIDTH // 2, 5),),
                direction=Direction.DOWN,
            ),
        )
