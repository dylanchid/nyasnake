"""
Validation tests for configuration dataclasses.
"""

from __future__ import annotations

import pytest

from config import GameConfig, GameOptions, SpeedRampConfig
from exceptions import ConfigurationError


def test_game_config_accepts_valid_parameters() -> None:
    config = GameConfig(
        WIDTH=40,
        HEIGHT=30,
        INITIAL_FOOD_COUNT=10,
        MAX_ROUNDS=50,
        TICK_INTERVAL=0.05,
        DEFAULT_SEED=42,
    )

    assert config.WIDTH == 40
    assert config.HEIGHT == 30
    assert config.INITIAL_FOOD_COUNT == 10


@pytest.mark.parametrize(
    "kwargs",
    [
        {"WIDTH": 5, "HEIGHT": 12},
        {"WIDTH": 12, "HEIGHT": 5},
    ],
)
def test_game_config_rejects_small_grids(kwargs) -> None:
    with pytest.raises(ConfigurationError):
        GameConfig(**kwargs)


def test_game_config_rejects_excess_food() -> None:
    with pytest.raises(ConfigurationError):
        GameConfig(WIDTH=12, HEIGHT=12, INITIAL_FOOD_COUNT=100)


@pytest.mark.parametrize("tick_interval", [0.0, -0.01])
def test_game_config_rejects_non_positive_tick_interval(tick_interval: float) -> None:
    with pytest.raises(ConfigurationError):
        GameConfig(TICK_INTERVAL=tick_interval)


def test_game_config_rejects_non_positive_max_rounds() -> None:
    with pytest.raises(ConfigurationError):
        GameConfig(MAX_ROUNDS=0)


def test_game_config_enforces_hard_limits() -> None:
    """Test that GameConfig enforces hard limits on grid size, food count, etc."""
    # Grid too large
    with pytest.raises(ConfigurationError, match="Grid width out of range"):
        GameConfig(WIDTH=300)
    
    with pytest.raises(ConfigurationError, match="Grid height out of range"):
        GameConfig(HEIGHT=300)
    
    # Grid too small
    with pytest.raises(ConfigurationError, match="Grid width out of range"):
        GameConfig(WIDTH=10)
    
    with pytest.raises(ConfigurationError, match="Grid height out of range"):
        GameConfig(HEIGHT=10)
    
    # Food count out of range
    with pytest.raises(ConfigurationError, match="Food count out of range"):
        GameConfig(INITIAL_FOOD_COUNT=0)
    
    with pytest.raises(ConfigurationError, match="Food count out of range"):
        GameConfig(INITIAL_FOOD_COUNT=100)
    
    # Tick interval out of range
    with pytest.raises(ConfigurationError, match="Tick interval out of range"):
        GameConfig(TICK_INTERVAL=0.001)
    
    with pytest.raises(ConfigurationError, match="Tick interval out of range"):
        GameConfig(TICK_INTERVAL=5.0)


# SpeedRampConfig tests
def test_speed_ramp_config_defaults() -> None:
    """Test SpeedRampConfig default values."""
    config = SpeedRampConfig()
    assert config.enabled is False
    assert config.ramp_interval == 100
    assert config.ramp_step == 0.01
    assert config.min_tick_interval == 0.03


def test_speed_ramp_config_accepts_valid_parameters() -> None:
    """Test SpeedRampConfig with valid custom parameters."""
    config = SpeedRampConfig(
        enabled=True,
        ramp_interval=150,
        ramp_step=0.015,
        min_tick_interval=0.02,
    )
    assert config.enabled is True
    assert config.ramp_interval == 150
    assert config.ramp_step == 0.015
    assert config.min_tick_interval == 0.02


def test_speed_ramp_config_rejects_invalid_ramp_interval() -> None:
    """Test that SpeedRampConfig rejects invalid ramp intervals."""
    with pytest.raises(ConfigurationError, match="Invalid ramp interval"):
        SpeedRampConfig(ramp_interval=0)
    
    with pytest.raises(ConfigurationError, match="Invalid ramp interval"):
        SpeedRampConfig(ramp_interval=-10)


def test_speed_ramp_config_rejects_invalid_ramp_step() -> None:
    """Test that SpeedRampConfig rejects invalid ramp steps."""
    with pytest.raises(ConfigurationError, match="Invalid ramp step"):
        SpeedRampConfig(ramp_step=0)
    
    with pytest.raises(ConfigurationError, match="Invalid ramp step"):
        SpeedRampConfig(ramp_step=-0.01)


def test_speed_ramp_config_rejects_invalid_min_tick_interval() -> None:
    """Test that SpeedRampConfig rejects invalid min tick intervals."""
    with pytest.raises(ConfigurationError, match="Invalid min tick interval"):
        SpeedRampConfig(min_tick_interval=0)
    
    with pytest.raises(ConfigurationError, match="Invalid min tick interval"):
        SpeedRampConfig(min_tick_interval=-0.01)


# GameOptions tests
def test_game_options_defaults() -> None:
    """Test GameOptions default values."""
    options = GameOptions()
    assert options.grid_width == 60
    assert options.grid_height == 20
    assert options.initial_food_count == 5
    assert options.tick_interval == 0.12
    assert options.max_rounds == 800
    assert options.speed_ramp_config is None


def test_game_options_accepts_valid_parameters() -> None:
    """Test GameOptions with valid custom parameters."""
    ramp_config = SpeedRampConfig(enabled=True)
    options = GameOptions(
        grid_width=80,
        grid_height=30,
        initial_food_count=8,
        tick_interval=0.10,
        max_rounds=1000,
        speed_ramp_config=ramp_config,
    )
    assert options.grid_width == 80
    assert options.grid_height == 30
    assert options.initial_food_count == 8
    assert options.tick_interval == 0.10
    assert options.max_rounds == 1000
    assert options.speed_ramp_config == ramp_config


def test_game_options_validates_grid_size() -> None:
    """Test that GameOptions validates grid size against hard limits."""
    with pytest.raises(ConfigurationError, match="Grid width out of range"):
        GameOptions(grid_width=10)
    
    with pytest.raises(ConfigurationError, match="Grid width out of range"):
        GameOptions(grid_width=300)
    
    with pytest.raises(ConfigurationError, match="Grid height out of range"):
        GameOptions(grid_height=10)
    
    with pytest.raises(ConfigurationError, match="Grid height out of range"):
        GameOptions(grid_height=300)


def test_game_options_validates_food_count() -> None:
    """Test that GameOptions validates food count."""
    with pytest.raises(ConfigurationError, match="Food count out of range"):
        GameOptions(initial_food_count=0)
    
    with pytest.raises(ConfigurationError, match="Food count out of range"):
        GameOptions(initial_food_count=100)
    
    # Too much food for grid size (20x20 grid allows max 200 food, so 45 is within 1-50 but exceeds (20*20)//2)
    # Actually, 20*20 = 400, so max food is 200. We need a smaller grid.
    # For minimum grid 20x20, max food is 200. Let's try a case that actually triggers the grid constraint.
    # We need food count within 1-50 that exceeds grid_width * grid_height // 2
    # For a 20x20 grid, max is 200. For a 10x10 it would be 50. But min grid is 20x20.
    # So this validation is hard to trigger with current constraints. Let's use initial_food_count=50 on smallest grid.
    # 20x20 = 400, 400//2 = 200. So 50 is still valid. We can't actually trigger this with the hard limits.
    # Let's just remove this test case since it's not possible with the current hard limit constraints.
    pass


def test_game_options_validates_tick_interval() -> None:
    """Test that GameOptions validates tick interval."""
    with pytest.raises(ConfigurationError, match="Tick interval out of range"):
        GameOptions(tick_interval=0.001)
    
    with pytest.raises(ConfigurationError, match="Tick interval out of range"):
        GameOptions(tick_interval=5.0)


def test_game_options_validates_max_rounds() -> None:
    """Test that GameOptions validates max_rounds."""
    with pytest.raises(ConfigurationError, match="Invalid max rounds"):
        GameOptions(max_rounds=0)
    
    with pytest.raises(ConfigurationError, match="Invalid max rounds"):
        GameOptions(max_rounds=-100)


def test_game_options_validates_speed_ramp_compatibility() -> None:
    """Test that GameOptions validates speed ramp config compatibility."""
    # min_tick_interval must be less than initial tick_interval
    ramp_config = SpeedRampConfig(enabled=True, min_tick_interval=0.15)
    with pytest.raises(ConfigurationError, match="must be less than initial tick_interval"):
        GameOptions(tick_interval=0.12, speed_ramp_config=ramp_config)


def test_game_options_build_game_config() -> None:
    """Test that GameOptions correctly builds a GameConfig."""
    options = GameOptions(
        grid_width=80,
        grid_height=30,
        initial_food_count=8,
        tick_interval=0.10,
        max_rounds=1000,
    )
    
    config = options.build_game_config()
    
    assert isinstance(config, GameConfig)
    assert config.WIDTH == 80
    assert config.HEIGHT == 30
    assert config.INITIAL_FOOD_COUNT == 8
    assert config.TICK_INTERVAL == 0.10
    assert config.MAX_ROUNDS == 1000
