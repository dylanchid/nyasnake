"""
Configuration constants for the snake AI system.
Centralizes all magic numbers for easy tuning.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

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

    # Hard limits for runtime configuration
    MIN_GRID_SIZE: int = 20
    MAX_GRID_SIZE: int = 200
    MIN_FOOD_COUNT: int = 1
    MAX_FOOD_COUNT: int = 50
    MIN_TICK_INTERVAL: float = 0.01
    MAX_TICK_INTERVAL: float = 2.0

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.WIDTH < self.MIN_GRID_SIZE or self.WIDTH > self.MAX_GRID_SIZE:
            raise ConfigurationError(
                f"Grid width out of range: {self.WIDTH} "
                f"(must be between {self.MIN_GRID_SIZE} and {self.MAX_GRID_SIZE})"
            )
        if self.HEIGHT < self.MIN_GRID_SIZE or self.HEIGHT > self.MAX_GRID_SIZE:
            raise ConfigurationError(
                f"Grid height out of range: {self.HEIGHT} "
                f"(must be between {self.MIN_GRID_SIZE} and {self.MAX_GRID_SIZE})"
            )
        if self.INITIAL_FOOD_COUNT < self.MIN_FOOD_COUNT or self.INITIAL_FOOD_COUNT > self.MAX_FOOD_COUNT:
            raise ConfigurationError(
                f"Food count out of range: {self.INITIAL_FOOD_COUNT} "
                f"(must be between {self.MIN_FOOD_COUNT} and {self.MAX_FOOD_COUNT})"
            )
        if self.INITIAL_FOOD_COUNT > (self.WIDTH * self.HEIGHT) // 2:
            raise ConfigurationError(
                f"Too much food for grid size: {self.INITIAL_FOOD_COUNT} food in "
                f"{self.WIDTH}x{self.HEIGHT} grid (maximum {(self.WIDTH * self.HEIGHT) // 2})"
            )
        if self.TICK_INTERVAL < self.MIN_TICK_INTERVAL or self.TICK_INTERVAL > self.MAX_TICK_INTERVAL:
            raise ConfigurationError(
                f"Tick interval out of range: {self.TICK_INTERVAL} "
                f"(must be between {self.MIN_TICK_INTERVAL} and {self.MAX_TICK_INTERVAL})"
            )
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


@dataclass(frozen=True)
class SpeedRampConfig:
    """Configuration for progressive speed increases during gameplay."""
    enabled: bool = False
    ramp_interval: int = 100  # frames between speed increases
    ramp_step: float = 0.01  # tick interval reduction per ramp (seconds)
    min_tick_interval: float = 0.03  # minimum tick interval (speed cap)

    def __post_init__(self) -> None:
        """Validate speed ramp parameters."""
        if self.ramp_interval <= 0:
            raise ConfigurationError(f"Invalid ramp interval: {self.ramp_interval} (must be > 0)")
        if self.ramp_step <= 0:
            raise ConfigurationError(f"Invalid ramp step: {self.ramp_step} (must be > 0)")
        if self.min_tick_interval <= 0:
            raise ConfigurationError(
                f"Invalid min tick interval: {self.min_tick_interval} (must be > 0)"
            )


@dataclass(frozen=True)
class GameOptions:
    """Runtime-configurable game options that can be set via CLI or presets."""
    grid_width: int = 60
    grid_height: int = 20
    initial_food_count: int = 5
    tick_interval: float = 0.12
    max_rounds: int = 800
    speed_ramp_config: Optional[SpeedRampConfig] = None

    def __post_init__(self) -> None:
        """Validate game options."""
        # Validate against GameConfig hard limits
        if self.grid_width < GameConfig.MIN_GRID_SIZE or self.grid_width > GameConfig.MAX_GRID_SIZE:
            raise ConfigurationError(
                f"Grid width out of range: {self.grid_width} "
                f"(must be between {GameConfig.MIN_GRID_SIZE} and {GameConfig.MAX_GRID_SIZE})"
            )
        if self.grid_height < GameConfig.MIN_GRID_SIZE or self.grid_height > GameConfig.MAX_GRID_SIZE:
            raise ConfigurationError(
                f"Grid height out of range: {self.grid_height} "
                f"(must be between {GameConfig.MIN_GRID_SIZE} and {GameConfig.MAX_GRID_SIZE})"
            )
        if self.initial_food_count < GameConfig.MIN_FOOD_COUNT or self.initial_food_count > GameConfig.MAX_FOOD_COUNT:
            raise ConfigurationError(
                f"Food count out of range: {self.initial_food_count} "
                f"(must be between {GameConfig.MIN_FOOD_COUNT} and {GameConfig.MAX_FOOD_COUNT})"
            )
        if self.initial_food_count > (self.grid_width * self.grid_height) // 2:
            raise ConfigurationError(
                f"Too much food for grid size: {self.initial_food_count} food in "
                f"{self.grid_width}x{self.grid_height} grid (maximum {(self.grid_width * self.grid_height) // 2})"
            )
        if self.tick_interval < GameConfig.MIN_TICK_INTERVAL or self.tick_interval > GameConfig.MAX_TICK_INTERVAL:
            raise ConfigurationError(
                f"Tick interval out of range: {self.tick_interval} "
                f"(must be between {GameConfig.MIN_TICK_INTERVAL} and {GameConfig.MAX_TICK_INTERVAL})"
            )
        if self.max_rounds <= 0:
            raise ConfigurationError(f"Invalid max rounds: {self.max_rounds} (must be > 0)")
        
        # Validate speed ramp compatibility
        if self.speed_ramp_config and self.speed_ramp_config.enabled:
            if self.speed_ramp_config.min_tick_interval >= self.tick_interval:
                raise ConfigurationError(
                    f"Speed ramp min_tick_interval ({self.speed_ramp_config.min_tick_interval}) "
                    f"must be less than initial tick_interval ({self.tick_interval})"
                )
            # Ensure ramping won't exceed max_rounds before hitting minimum
            max_ramps = (self.tick_interval - self.speed_ramp_config.min_tick_interval) / self.speed_ramp_config.ramp_step
            frames_needed = max_ramps * self.speed_ramp_config.ramp_interval
            if frames_needed > self.max_rounds * 2:
                # Just a warning - allow it but it means ramp might not complete
                pass

    def build_game_config(self) -> GameConfig:
        """Construct a GameConfig from these options."""
        return GameConfig(
            WIDTH=self.grid_width,
            HEIGHT=self.grid_height,
            INITIAL_FOOD_COUNT=self.initial_food_count,
            TICK_INTERVAL=self.tick_interval,
            MAX_ROUNDS=self.max_rounds,
        )


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
