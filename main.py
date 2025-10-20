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
    GameOptions,
    SpeedRampConfig,
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
    default_game = get_default_game_config()
    parser = argparse.ArgumentParser(description="Nyasnake arena")
    
    # Existing flags (backward compatibility)
    parser.add_argument("--seed", type=int, help="Seed RNG for reproducible simulations.")
    parser.add_argument("--tick-interval", type=float, help="Seconds between frames.")
    parser.add_argument("--tick-rate", type=float, help="Frames per second. Overrides tick-interval if provided.")
    parser.add_argument("--ai-level", choices=["easy", "normal", "hard"], default="normal", help="Select AI difficulty preset.")
    parser.add_argument("--interactive", action="store_true", help="Enable keyboard controls for snake 0 (WASD).")
    parser.add_argument("--log-level", default=default_debug.LOG_LEVEL, choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--debug", action="store_true", help="Enable debug overlays while rendering.")
    
    # New configuration flags
    parser.add_argument("--width", type=int, help=f"Grid width (default: {default_game.WIDTH}, range: {default_game.MIN_GRID_SIZE}-{default_game.MAX_GRID_SIZE}).")
    parser.add_argument("--height", type=int, help=f"Grid height (default: {default_game.HEIGHT}, range: {default_game.MIN_GRID_SIZE}-{default_game.MAX_GRID_SIZE}).")
    parser.add_argument("--food-count", type=int, help=f"Initial food count (default: {default_game.INITIAL_FOOD_COUNT}, range: {default_game.MIN_FOOD_COUNT}-{default_game.MAX_FOOD_COUNT}).")
    parser.add_argument("--max-rounds", type=int, help=f"Maximum number of rounds (default: {default_game.MAX_ROUNDS}).")
    
    # Difficulty preset flag
    parser.add_argument(
        "--difficulty",
        choices=["easy", "normal", "hard", "extreme", "custom"],
        default="custom",
        help="Difficulty preset (bundled settings for grid, speed, food). Use 'custom' for manual configuration."
    )
    
    # Speed ramping flags
    parser.add_argument("--speed-ramp", action="store_true", help="Enable progressive speed increases during gameplay.")
    parser.add_argument("--ramp-interval", type=int, default=100, help="Frames between speed increases (default: 100).")
    parser.add_argument("--ramp-step", type=float, default=0.01, help="Tick interval reduction per ramp in seconds (default: 0.01).")
    parser.add_argument("--min-tick", type=float, default=0.03, help="Minimum tick interval / maximum speed cap (default: 0.03).")
    
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


def get_difficulty_preset(difficulty: str) -> dict:
    """Return preset configuration values for each difficulty level."""
    presets = {
        "easy": {
            "grid_width": 40,
            "grid_height": 20,
            "initial_food_count": 8,
            "tick_interval": 0.15,
            "max_rounds": 600,
            "speed_ramp_enabled": False,
        },
        "normal": {
            "grid_width": 60,
            "grid_height": 20,
            "initial_food_count": 5,
            "tick_interval": 0.12,
            "max_rounds": 800,
            "speed_ramp_enabled": False,
        },
        "hard": {
            "grid_width": 80,
            "grid_height": 30,
            "initial_food_count": 4,
            "tick_interval": 0.10,
            "max_rounds": 1000,
            "speed_ramp_enabled": True,
            "ramp_interval": 150,
            "ramp_step": 0.01,
            "min_tick_interval": 0.04,
        },
        "extreme": {
            "grid_width": 100,
            "grid_height": 40,
            "initial_food_count": 3,
            "tick_interval": 0.08,
            "max_rounds": 1500,
            "speed_ramp_enabled": True,
            "ramp_interval": 100,
            "ramp_step": 0.015,
            "min_tick_interval": 0.02,
        },
    }
    return presets.get(difficulty, {})


def build_game_options(args: argparse.Namespace) -> GameOptions:
    """Construct GameOptions from CLI arguments, applying presets as needed."""
    default_game = get_default_game_config()
    
    # Start with difficulty preset if not custom
    if args.difficulty != "custom":
        preset = get_difficulty_preset(args.difficulty)
    else:
        preset = {}
    
    # CLI args override preset values
    grid_width = args.width if args.width is not None else preset.get("grid_width", default_game.WIDTH)
    grid_height = args.height if args.height is not None else preset.get("grid_height", default_game.HEIGHT)
    initial_food_count = args.food_count if args.food_count is not None else preset.get("initial_food_count", default_game.INITIAL_FOOD_COUNT)
    max_rounds = args.max_rounds if args.max_rounds is not None else preset.get("max_rounds", default_game.MAX_ROUNDS)
    
    # Determine tick interval (backward compatibility with --tick-rate and --tick-interval)
    tick_interval = preset.get("tick_interval", default_game.TICK_INTERVAL)
    if args.tick_rate:
        tick_interval = 1.0 / max(args.tick_rate, 1e-3)
    elif args.tick_interval is not None:
        tick_interval = args.tick_interval
    
    # Speed ramping configuration
    speed_ramp_enabled = args.speed_ramp or preset.get("speed_ramp_enabled", False)
    speed_ramp_config = None
    if speed_ramp_enabled:
        speed_ramp_config = SpeedRampConfig(
            enabled=True,
            ramp_interval=preset.get("ramp_interval", args.ramp_interval),
            ramp_step=preset.get("ramp_step", args.ramp_step),
            min_tick_interval=preset.get("min_tick_interval", args.min_tick),
        )
    
    return GameOptions(
        grid_width=grid_width,
        grid_height=grid_height,
        initial_food_count=initial_food_count,
        tick_interval=tick_interval,
        max_rounds=max_rounds,
        speed_ramp_config=speed_ramp_config,
    )


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)
    
    # Build game options from CLI args (with preset support)
    game_options = build_game_options(args)
    game_config = game_options.build_game_config()
    
    # Create other config instances (no global singletons!)
    display_config = get_default_display_config()
    ai_config = get_default_ai_config()
    debug_config = configure_debug(args.debug, args.log_level)

    logger = logging.getLogger("nyasnake")
    logger.info("Starting Nyasnake")

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
        tick_interval=game_options.tick_interval,
        speed_ramp_config=game_options.speed_ramp_config,
        game_config=game_config,
        display_config=display_config,
        debug_config=debug_config,
        ai_controller=ai_controller,
        renderer=renderer,
    )

    # Enhanced startup banner
    banner = "=" * game_config.WIDTH
    print(banner)
    print("🐍  Nyasnake Arena")
    print(banner)
    
    # Show difficulty preset if used
    if args.difficulty != "custom":
        print(f"Difficulty: {args.difficulty.upper()}")
    
    # Show configuration details
    print(f"Grid: {game_config.WIDTH}x{game_config.HEIGHT}")
    print(f"Snakes: {len(profiles)} | Food: {game_config.INITIAL_FOOD_COUNT} | Max rounds: {game_config.MAX_ROUNDS}")
    print(f"Initial speed: {game_options.tick_interval:.3f}s/tick", end="")
    
    # Show speed ramping info if enabled
    if game_options.speed_ramp_config and game_options.speed_ramp_config.enabled:
        ramp = game_options.speed_ramp_config
        print(f" → {ramp.min_tick_interval:.3f}s (ramps every {ramp.ramp_interval} frames)")
    else:
        print()
    
    print(f"Seed: {args.seed or runner.seed} | AI Level: {args.ai_level}")
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
