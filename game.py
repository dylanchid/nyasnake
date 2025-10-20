"""
Synchronous game runner with a phase-based loop and pluggable renderer/input.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from collections import deque
from dataclasses import dataclass
from random import Random
from typing import Callable, Deque, Dict, List, Mapping, MutableMapping, Optional, Protocol, Sequence

from config import AIPersonality, DebugConfig, DisplayConfig, GameConfig, SpeedRampConfig
from engine import (
    GameEvent,
    GameState,
    SnakeSpawn,
    SnakeState,
    TickResult,
    advance_state,
    create_initial_state,
)
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


class SnakeController(Protocol):
    """Controller that makes a decision for a specific snake."""

    def decide(self, state: GameState, snake: SnakeState) -> Optional[Direction]:
        ...


class InputCommand(Protocol):
    """Command abstraction for applying inputs to the decision buffer."""

    def apply(self, decisions: MutableMapping[int, Direction]) -> None:
        ...


@dataclass(frozen=True)
class MoveCommand(InputCommand):
    """Concrete command that applies a move to a snake."""

    snake_id: int
    direction: Direction

    def apply(self, decisions: MutableMapping[int, Direction]) -> None:
        decisions[self.snake_id] = self.direction


class InputProvider:
    """Base class for user input providers."""

    def poll(self) -> Sequence[InputCommand]:
        """
        Collect commands for controllable snakes.
        Default implementation returns no overrides.
        """
        return ()

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
            self._setup_posix_terminal()

    def poll(self) -> Sequence[InputCommand]:
        commands: list[InputCommand] = []
        if self._is_windows:
            commands.extend(self._poll_windows())
        else:
            commands.extend(self._poll_posix())
        return commands

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

    def _poll_windows(self) -> List[InputCommand]:
        commands: List[InputCommand] = []
        try:
            import msvcrt  # type: ignore
        except ImportError:
            return commands

        while msvcrt.kbhit():
            char = msvcrt.getwch()
            if not char:
                continue
            mapping = self._bindings.get(char.lower())
            if mapping:
                snake_id, direction = mapping
                commands.append(MoveCommand(snake_id, direction))
        return commands

    def _poll_posix(self) -> List[InputCommand]:
        commands: List[InputCommand] = []
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
                commands.append(MoveCommand(snake_id, direction))
        return commands

    def _setup_posix_terminal(self) -> None:
        if not sys.stdin.isatty():
            return
        try:
            import termios
            import tty

            self._fd = sys.stdin.fileno()
            self._tty_attrs = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        except (termios.error, OSError, ValueError) as exc:  # pragma: no cover - platform specific
            logger.debug("Terminal manipulation not available: %s", exc)
            self._fd = None
            self._tty_attrs = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Unexpected terminal setup failure: %s", exc)
            self._fd = None
            self._tty_attrs = None


class Renderer:
    """Base class for rendering game state."""

    def __init__(
        self,
        display_config: DisplayConfig,
        debug_config: DebugConfig,
    ):
        self._display_config = display_config
        self._debug_config = debug_config

    @property
    def display_config(self) -> DisplayConfig:
        return self._display_config

    @property
    def debug_config(self) -> DebugConfig:
        return self._debug_config

    def render(
        self,
        state: GameState,
        profiles: Mapping[int, SnakeProfile],
        events: Sequence[GameEvent],
    ) -> None:
        raise NotImplementedError


class AnsiRenderer(Renderer):
    """ANSI terminal renderer used as the default fallback backend."""

    def render(
        self,
        state: GameState,
        profiles: Mapping[int, SnakeProfile],
        events: Sequence[GameEvent],
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
        if events and self.debug_config.LOG_DECISIONS:
            for event in events:
                print(f"  • Event: {event.type} (snake={event.snake_id}, pos={event.position})")

        if any(
            (
                self.debug_config.SHOW_DANGER_ZONES,
                self.debug_config.SHOW_PATHS,
                self.debug_config.SHOW_EVALUATION_SCORES,
            )
        ):
            print(
                "Debug Mode: "
                f"danger_zones={self.debug_config.SHOW_DANGER_ZONES}, "
                f"paths={self.debug_config.SHOW_PATHS}, "
                f"scores={self.debug_config.SHOW_EVALUATION_SCORES}"
            )

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

        print(f"\nFrame: {state.frame}")

    def _draw_border(self, grid: list[list[str]], width: int, height: int) -> None:
        symbols = self.display_config.SYMBOLS
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
                    f"{self.display_config.COLORS['yellow']}"
                    f"{self.display_config.SYMBOLS['food']}"
                    f"{self.display_config.COLORS['reset']}"
                )

    def _draw_snakes(
        self,
        grid: list[list[str]],
        state: GameState,
        profiles: Mapping[int, SnakeProfile],
    ) -> None:
        body_symbol = self.display_config.SYMBOLS["snake_body"]
        for snake in state.snakes:
            profile = profiles.get(snake.id)
            if not profile:
                continue
            color = profile.color if snake.alive else self.display_config.COLORS["gray"]
            for index, segment in enumerate(snake.body):
                if not (0 <= segment.x < state.width and 0 <= segment.y < state.height):
                    continue
                symbol = profile.symbol if index == 0 else body_symbol
                grid[segment.y][segment.x] = f"{color}{symbol}{self.display_config.COLORS['reset']}"

    def _print_status(self, state: GameState, profiles: Mapping[int, SnakeProfile]) -> None:
        for snake in state.snakes:
            profile = profiles.get(snake.id)
            if not profile:
                continue
            status = "ALIVE" if snake.alive else "DEAD"
            color = profile.color if snake.alive else self.display_config.COLORS["gray"]
            personality_name = profile.personality.name
            print(
                f"{color}{personality_name:11} Snake: {status:5} | "
                f"Score: {snake.score:4} | Length: {snake.length():3} | "
                f"Kills: {snake.kills}{self.display_config.COLORS['reset']}"
            )


@dataclass(frozen=True)
class StateMemento:
    """Snapshot of a game state for replay/memento purposes."""

    frame: int
    state: GameState


class StateHistory:
    """Maintains a bounded history of game states for replay or debugging."""

    def __init__(self, capacity: Optional[int] = None) -> None:
        self._capacity = capacity
        self._history: Deque[StateMemento] = deque()

    def record(self, state: GameState) -> None:
        self._history.append(StateMemento(frame=state.frame, state=state))
        if self._capacity is not None and len(self._history) > self._capacity:
            self._history.popleft()

    def rewind(self, steps: int = 1) -> Optional[StateMemento]:
        if steps <= 0 or steps > len(self._history):
            return None
        memento: Optional[StateMemento] = None
        for _ in range(steps):
            memento = self._history.pop()
        assert memento is not None
        return memento

    def snapshots(self) -> Sequence[StateMemento]:
        return tuple(self._history)


class GameEventVisitor(Protocol):
    """Visitor interface for processing game events."""

    def visit(self, event: GameEvent) -> None:
        ...


class EventDispatcher:
    """Coordinates event propagation via visitors and legacy listeners."""

    def __init__(self) -> None:
        self._listeners: list[Callable[[TickResult], None]] = []
        self._visitors: list[GameEventVisitor] = []

    def register_listener(self, listener: Callable[[TickResult], None]) -> None:
        self._listeners.append(listener)

    def register_visitor(self, visitor: GameEventVisitor) -> None:
        self._visitors.append(visitor)

    def dispatch(self, tick: TickResult) -> None:
        for event in tick.events:
            for visitor in self._visitors:
                try:
                    visitor.visit(event)
                except Exception:
                    logger.warning("Event visitor raised an exception", exc_info=True)

        for listener in self._listeners:
            try:
                listener(tick)
            except Exception:
                logger.warning("Event listener raised an exception", exc_info=True)


class DecisionCollector:
    """Aggregates AI decisions, user commands, and controller overrides."""

    def __init__(
        self,
        decision_provider: DecisionProvider,
        input_provider: Optional[InputProvider],
        overrides: Optional[Mapping[int, SnakeController]] = None,
    ):
        self._decision_provider = decision_provider
        self._input_provider = input_provider
        self._overrides: Dict[int, SnakeController] = dict(overrides or {})
        self._command_history: list[list[InputCommand]] = []

    def collect(self, state: GameState) -> Dict[int, Direction]:
        decisions = dict(self._decision_provider.decide(state))
        commands: list[InputCommand] = []

        if self._input_provider is not None:
            try:
                commands.extend(self._input_provider.poll())
            except OSError as exc:  # pragma: no cover - platform specific
                logger.warning("Input provider failed: %s", exc)

        commands.extend(self._collect_override_commands(state))

        for command in commands:
            command.apply(decisions)

        self._command_history.append(commands)
        return decisions

    def update_override(self, snake_id: int, controller: SnakeController) -> None:
        self._overrides[snake_id] = controller

    def remove_override(self, snake_id: int) -> None:
        self._overrides.pop(snake_id, None)

    def history(self) -> Sequence[Sequence[InputCommand]]:
        return tuple(tuple(cmds) for cmds in self._command_history)

    def _collect_override_commands(self, state: GameState) -> list[InputCommand]:
        commands: list[InputCommand] = []
        snakes_by_id = {snake.id: snake for snake in state.snakes if snake.alive}
        for snake_id, controller in self._overrides.items():
            snake = snakes_by_id.get(snake_id)
            if snake is None:
                continue
            override = controller.decide(state, snake)
            if override is not None:
                commands.append(MoveCommand(snake_id, override))
        return commands


class GameLoop:
    """Runs the main simulation loop leveraging injected collaborators."""

    def __init__(
        self,
        renderer: Renderer,
        decision_collector: DecisionCollector,
        event_dispatcher: EventDispatcher,
        history: StateHistory,
        rng: Random,
        desired_food: int,
        tick_interval: float,
        max_rounds: int,
        profiles: Mapping[int, SnakeProfile],
        initial_state: GameState,
        speed_ramp_config: Optional[SpeedRampConfig] = None,
    ):
        self._renderer = renderer
        self._decision_collector = decision_collector
        self._event_dispatcher = event_dispatcher
        self._history = history
        self._rng = rng
        self._desired_food = desired_food
        self._initial_tick_interval = tick_interval
        self._current_tick_interval = tick_interval
        self._max_rounds = max_rounds
        self._profiles = profiles
        self._state = initial_state
        self._game_over = False
        self._speed_ramp_config = speed_ramp_config
        self._frames_since_last_ramp = 0

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def current_tick_interval(self) -> float:
        """Return the current tick interval (may differ from initial if ramping)."""
        return self._current_tick_interval

    def run(self) -> GameState:
        while not self._should_stop():
            frame_start = time.perf_counter()
            self._history.record(self._state)
            decisions = self._decision_collector.collect(self._state)
            tick = advance_state(self._state, decisions, self._rng, self._desired_food)
            self._state = tick.state
            self._history.record(self._state)
            self._event_dispatcher.dispatch(tick)
            self._renderer.render(tick.state, self._profiles, tick.events)
            self._apply_speed_ramping()
            self._sleep_until_next_frame(frame_start)
        return self._state

    def _should_stop(self) -> bool:
        if self._game_over:
            return True
        if self._state.frame >= self._max_rounds:
            logger.info("Game over: reached max rounds (%s)", self._max_rounds)
            return True
        alive = [snake for snake in self._state.snakes if snake.alive]
        if len(alive) <= 1:
            logger.info("Game over: remaining snakes <= 1")
            self._game_over = True
            return True
        return False

    def _apply_speed_ramping(self) -> None:
        """Apply speed ramping if configured and conditions are met."""
        if not self._speed_ramp_config or not self._speed_ramp_config.enabled:
            return
        
        self._frames_since_last_ramp += 1
        
        if self._frames_since_last_ramp >= self._speed_ramp_config.ramp_interval:
            # Time to ramp up the speed
            new_interval = self._current_tick_interval - self._speed_ramp_config.ramp_step
            # Respect the minimum tick interval (max speed)
            if new_interval >= self._speed_ramp_config.min_tick_interval:
                self._current_tick_interval = new_interval
                logger.info(
                    "Speed ramped: tick_interval %.3f -> %.3f (frame %d)",
                    self._current_tick_interval + self._speed_ramp_config.ramp_step,
                    self._current_tick_interval,
                    self._state.frame,
                )
            else:
                # Hit the speed cap
                if self._current_tick_interval > self._speed_ramp_config.min_tick_interval:
                    self._current_tick_interval = self._speed_ramp_config.min_tick_interval
                    logger.info(
                        "Speed cap reached: tick_interval %.3f (frame %d)",
                        self._current_tick_interval,
                        self._state.frame,
                    )
            self._frames_since_last_ramp = 0

    def _sleep_until_next_frame(self, frame_start: float) -> None:
        elapsed = time.perf_counter() - frame_start
        remaining = self._current_tick_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)


class GameRunner:
    """Coordinates the game loop and orchestrates phases."""

    def __init__(
        self,
        profiles: Sequence[SnakeProfile],
        game_config: GameConfig,
        display_config: DisplayConfig,
        debug_config: DebugConfig,
        ai_controller: DecisionProvider,
        renderer: Optional[Renderer] = None,
        input_provider: Optional[InputProvider] = None,
        rng: Optional[Random] = None,
        seed: Optional[int] = None,
        tick_interval: Optional[float] = None,
        speed_ramp_config: Optional[SpeedRampConfig] = None,
        controller_overrides: Optional[Mapping[int, SnakeController]] = None,
        event_listeners: Optional[Sequence[Callable[[TickResult], None]]] = None,
        state_history_capacity: Optional[int] = None,
    ):
        if renderer is None:
            renderer = AnsiRenderer(display_config, debug_config)

        self._profiles = {profile.id: profile for profile in profiles}
        self._renderer = renderer
        self._input = input_provider or InputProvider()
        if rng is not None:
            self._rng = rng
            self._seed = None
        else:
            seed_value = seed if seed is not None else game_config.DEFAULT_SEED
            self._rng = Random(seed_value)
            self._seed = seed_value

        self._tick_interval = tick_interval if tick_interval is not None else game_config.TICK_INTERVAL
        self._desired_food = game_config.INITIAL_FOOD_COUNT
        self._game_config = game_config
        self._debug_config = debug_config

        initial_state = create_initial_state(
            game_config.WIDTH,
            game_config.HEIGHT,
            self._default_spawns(game_config),
            game_config.INITIAL_FOOD_COUNT,
            self._rng,
        )

        self._history = StateHistory(capacity=state_history_capacity)
        self._event_dispatcher = EventDispatcher()
        for listener in event_listeners or ():
            self._event_dispatcher.register_listener(listener)

        self._decision_collector = DecisionCollector(
            decision_provider=ai_controller,
            input_provider=self._input,
            overrides=controller_overrides,
        )

        self._loop = GameLoop(
            renderer=self._renderer,
            decision_collector=self._decision_collector,
            event_dispatcher=self._event_dispatcher,
            history=self._history,
            rng=self._rng,
            desired_food=self._desired_food,
            tick_interval=self._tick_interval,
            max_rounds=game_config.MAX_ROUNDS,
            profiles=self._profiles,
            initial_state=initial_state,
            speed_ramp_config=speed_ramp_config,
        )

    @property
    def state(self) -> GameState:
        return self._loop.state

    @property
    def seed(self) -> Optional[int]:
        return self._seed

    @property
    def profiles(self) -> Mapping[int, SnakeProfile]:
        return self._profiles

    @property
    def history(self) -> StateHistory:
        return self._history

    @property
    def command_history(self) -> Sequence[Sequence[InputCommand]]:
        return self._decision_collector.history()

    def run(self) -> None:
        """Run until completion or interruption."""
        try:
            self._loop.run()
        finally:
            # Ensure the final state is rendered at least once without events.
            self._renderer.render(self.state, self._profiles, ())
            self._input.close()

    def add_controller_override(self, snake_id: int, controller: SnakeController) -> None:
        self._decision_collector.update_override(snake_id, controller)

    def remove_controller_override(self, snake_id: int) -> None:
        self._decision_collector.remove_override(snake_id)

    def add_event_listener(self, listener: Callable[[TickResult], None]) -> None:
        self._event_dispatcher.register_listener(listener)

    def add_event_visitor(self, visitor: GameEventVisitor) -> None:
        self._event_dispatcher.register_visitor(visitor)

    def _default_spawns(self, game_config: GameConfig) -> Sequence[SnakeSpawn]:
        """Initial spawn configuration for the default three snakes."""
        return (
            SnakeSpawn(
                id=0,
                body=(Position(10, 10),),
                direction=Direction.RIGHT,
            ),
            SnakeSpawn(
                id=1,
                body=(Position(game_config.WIDTH - 10, 10),),
                direction=Direction.LEFT,
            ),
            SnakeSpawn(
                id=2,
                body=(Position(game_config.WIDTH // 2, 5),),
                direction=Direction.DOWN,
            ),
        )
