"""
Configuration constants for the snake AI system.
Centralizes all magic numbers for easy tuning.
"""

from dataclasses import dataclass
from enum import Enum


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


# Global singletons
GAME_CONFIG = GameConfig()
AI_CONFIG = AIConfig()
DISPLAY_CONFIG = DisplayConfig()
DEBUG_CONFIG = DebugConfig()
