"""
Configuration constants for the snake AI system.
Centralizes all magic numbers for easy tuning.
"""

from dataclasses import dataclass
from enum import Enum

from exceptions import ConfigurationError


class AIPersonality(Enum):
    """AI behavior personalities"""
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    BALANCED = "balanced"


@dataclass(frozen=True)
class GameConfig:
    """Game world configuration"""
    WIDTH: int = 60
    HEIGHT: int = 20
    INITIAL_FOOD_COUNT: int = 5
    MAX_ROUNDS: int = 800
    TICK_INTERVAL: float = 0.12  # seconds between updates
    DEFAULT_SEED: int = 1337

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.WIDTH < 10 or self.HEIGHT < 10:
            raise ConfigurationError(f"Grid too small: {self.WIDTH}x{self.HEIGHT} (minimum 10x10)")
        if self.INITIAL_FOOD_COUNT > (self.WIDTH * self.HEIGHT) // 2:
            raise ConfigurationError(
                f"Too much food for grid size: {self.INITIAL_FOOD_COUNT} food in "
                f"{self.WIDTH}x{self.HEIGHT} grid (maximum {(self.WIDTH * self.HEIGHT) // 2})"
            )
        if self.TICK_INTERVAL <= 0:
            raise ConfigurationError(f"Invalid tick interval: {self.TICK_INTERVAL} (must be > 0)")
        if self.MAX_ROUNDS <= 0:
            raise ConfigurationError(f"Invalid max rounds: {self.MAX_ROUNDS} (must be > 0)")


@dataclass(frozen=True)
class AIConfig:
    """Simplified AI configuration."""

    SPACE_SEARCH_LIMIT: int = 18  # Maximum flood-fill depth for space heuristic
    MAX_PATH_LENGTH: int = 64  # Cap for path length evaluation


@dataclass(frozen=True)
class DisplayConfig:
    """Visual display configuration"""
    COLORS = {
        'red': '\033[91m',
        'green': '\033[92m',
        'blue': '\033[94m',
        'yellow': '\033[93m',
        'gray': '\033[90m',
        'cyan': '\033[96m',
        'magenta': '\033[95m',
        'reset': '\033[0m'
    }
    
    SYMBOLS = {
        'snake_head': '█',
        'snake_body': '●',
        'food': '●',
        'border_h': '═',
        'border_v': '║',
        'corner_tl': '╔',
        'corner_tr': '╗',
        'corner_bl': '╚',
        'corner_br': '╝',
        'danger_zone': '×',
        'path_marker': '·',
    }


@dataclass(frozen=True)
class DebugConfig:
    """Debug visualization configuration"""
    SHOW_DANGER_ZONES: bool = False
    SHOW_PATHS: bool = False
    SHOW_EVALUATION_SCORES: bool = False
    LOG_DECISIONS: bool = True
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR


# Default configuration instances (not singletons - create new instances as needed)
def get_default_game_config() -> GameConfig:
    """Get a default game configuration instance."""
    return GameConfig()


def get_default_ai_config() -> AIConfig:
    """Get a default AI configuration instance."""
    return AIConfig()


def get_default_display_config() -> DisplayConfig:
    """Get a default display configuration instance."""
    return DisplayConfig()


def get_default_debug_config() -> DebugConfig:
    """Get a default debug configuration instance."""
    return DebugConfig()
