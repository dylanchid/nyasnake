"""
Validation tests for configuration dataclasses.
"""

from __future__ import annotations

import pytest

from config import GameConfig
from exceptions import ConfigurationError


def test_game_config_accepts_valid_parameters() -> None:
    config = GameConfig(
        WIDTH=20,
        HEIGHT=15,
        INITIAL_FOOD_COUNT=10,
        MAX_ROUNDS=50,
        TICK_INTERVAL=0.05,
        DEFAULT_SEED=42,
    )

    assert config.WIDTH == 20
    assert config.HEIGHT == 15
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
