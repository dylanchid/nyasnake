"""
Command-line entry point for the Nyasnake simulation.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Optional

from config import (
    AIConfig,
    AIPersonality,
    DebugConfig,
    DisplayConfig,
    GameConfig,
    get_default_ai_config,
    get_default_debug_config,
    get_default_display_config,
    get_default_game_config,
)
from exceptions import ConfigurationError, TerminalError
from factories import AIControllerFactory, RendererFactory
from game import GameRunner, KeyboardInput, SnakeProfile
from models import Direction


def setup_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(levelname)-8s [%(name)s] %(message)s",
    )


def parse_args() -> argparse.Namespace:
    default_debug = get_default_debug_config()
    parser = argparse.ArgumentParser(description="Nyasnake arena")
    parser.add_argument("--seed", type=int, help="Seed RNG for reproducible simulations.")
    parser.add_argument("--tick-interval", type=float, help="Seconds between frames.")
    parser.add_argument("--tick-rate", type=float, help="Frames per second. Overrides tick-interval if provided.")
    parser.add_argument("--ai-level", choices=["easy", "normal", "hard"], default="normal", help="Select AI difficulty preset.")
    parser.add_argument("--interactive", action="store_true", help="Enable keyboard controls for snake 0 (WASD).")
    parser.add_argument("--log-level", default=default_debug.LOG_LEVEL, choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--debug", action="store_true", help="Enable debug overlays while rendering.")
    return parser.parse_args()


def build_profiles(display_config: DisplayConfig) -> List[SnakeProfile]:
    colors = display_config.COLORS
    symbols = display_config.SYMBOLS
    return [
        SnakeProfile(
            id=0,
            personality=AIPersonality.AGGRESSIVE,
            color=colors["red"],
            symbol=symbols["snake_head"],
        ),
        SnakeProfile(
            id=1,
            personality=AIPersonality.DEFENSIVE,
            color=colors["green"],
            symbol="▓",
        ),
        SnakeProfile(
            id=2,
            personality=AIPersonality.BALANCED,
            color=colors["blue"],
            symbol="▒",
        ),
    ]


def create_input_provider(interactive: bool) -> Optional[KeyboardInput]:
    if not interactive:
        return None
    bindings = {
        "w": (0, Direction.UP),
        "s": (0, Direction.DOWN),
        "a": (0, Direction.LEFT),
        "d": (0, Direction.RIGHT),
    }
    return KeyboardInput(bindings)


def configure_debug(debug_enabled: bool, log_level: str) -> DebugConfig:
    """Create a debug config based on CLI flags."""
    if not debug_enabled:
        return DebugConfig(LOG_LEVEL=log_level)
    return DebugConfig(
        SHOW_DANGER_ZONES=True,
        SHOW_PATHS=False,
        SHOW_EVALUATION_SCORES=False,
        LOG_DECISIONS=True,
        LOG_LEVEL=log_level,
    )


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)
    
    # Create config instances (no global singletons!)
    game_config = get_default_game_config()
    display_config = get_default_display_config()
    ai_config = get_default_ai_config()
    debug_config = configure_debug(args.debug, args.log_level)

    logger = logging.getLogger("nyasnake")
    logger.info("Starting Nyasnake")

    tick_interval = args.tick_interval
    if args.tick_rate:
        tick_interval = 1.0 / max(args.tick_rate, 1e-3)
    if tick_interval is None:
        tick_interval = game_config.TICK_INTERVAL

    profiles = build_profiles(display_config)
    input_provider = create_input_provider(args.interactive)
    ai_factory = AIControllerFactory(ai_config)
    renderer_factory = RendererFactory(display_config, debug_config)
    ai_controller = ai_factory.create(args.ai_level, profiles)
    renderer = renderer_factory.create()

    runner = GameRunner(
        profiles=profiles,
        input_provider=input_provider,
        seed=args.seed,
        tick_interval=tick_interval,
        game_config=game_config,
        display_config=display_config,
        debug_config=debug_config,
        ai_controller=ai_controller,
        renderer=renderer,
    )

    banner = "=" * game_config.WIDTH
    print(banner)
    print("🐍  Nyasnake Arena")
    print(banner)
    print(f"Snakes: {len(profiles)} | Tick interval: {tick_interval:.3f}s | Seed: {args.seed or runner.seed}")
    print("Press Ctrl+C to exit.\n")

    try:
        runner.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        print("\nSimulation interrupted.")
        return

    final_state = runner.state
    alive = [snake for snake in final_state.snakes if snake.alive]
    print("\n" + banner)
    if alive:
        winner = alive[0]
        profile = runner.profiles[winner.id]
        print(f"🏆 Winner: {profile.personality.name} Snake (Score {winner.score})")
    else:
        print("No survivors this time.")

    print("\nFinal standings:")
    for snake in final_state.snakes:
        profile = runner.profiles[snake.id]
        status = "ALIVE" if snake.alive else "DEAD"
        print(
            f"  {profile.personality.name:11} | {status:5} | "
            f"Score {snake.score:4} | Length {snake.length():3} | Kills {snake.kills}"
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # User interrupted - this is normal, don't log as error
        print("\nSimulation interrupted by user.")
        sys.exit(0)
    except ConfigurationError as exc:
        # Configuration validation errors
        logging.error("Configuration error: %s", exc)
        sys.exit(1)
    except TerminalError as exc:
        # Terminal/input errors
        logging.error("Terminal error: %s", exc)
        sys.exit(1)
    except (ValueError, TypeError, AttributeError) as exc:
        # Other configuration or setup errors
        logging.error("Setup error: %s", exc)
        sys.exit(1)
    except OSError as exc:
        # System/IO errors (file system, etc.)
        logging.error("System error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        # Unexpected errors - log with full traceback
        logging.exception("Unexpected error: %s", exc)
        sys.exit(1)
