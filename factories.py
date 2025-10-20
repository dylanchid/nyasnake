"""
Factory utilities for constructing AI controllers and renderers.
"""

from __future__ import annotations

from typing import Sequence

from ai import GreedyAIController, SnakeStrategy, StrategyFactory
from config import AIConfig, AIPersonality, DebugConfig, DisplayConfig
from game import AnsiRenderer, Renderer, SnakeProfile


class AIControllerFactory:
    """Factory for building AI controllers based on difficulty presets."""

    def __init__(self, ai_config: AIConfig, strategy_factory: StrategyFactory | None = None) -> None:
        self._ai_config = ai_config
        self._strategy_factory = strategy_factory or StrategyFactory()

    def create(self, ai_level: str, profiles: Sequence[SnakeProfile]) -> GreedyAIController:
        strategies = {
            profile.id: SnakeStrategy(self._select_personality(ai_level, profile.personality))
            for profile in profiles
        }
        return GreedyAIController(strategies, self._ai_config, self._strategy_factory)

    def _select_personality(self, ai_level: str, default: AIPersonality) -> AIPersonality:
        if ai_level == "easy":
            return AIPersonality.DEFENSIVE
        if ai_level == "hard":
            return AIPersonality.AGGRESSIVE
        return default


class RendererFactory:
    """Factory responsible for instantiating renderer implementations."""

    def __init__(self, display_config: DisplayConfig, debug_config: DebugConfig) -> None:
        self._display_config = display_config
        self._debug_config = debug_config

    def create(self, renderer_type: str = "ansi") -> Renderer:
        if renderer_type == "ansi":
            return AnsiRenderer(self._display_config, self._debug_config)
        raise ValueError(f"Unknown renderer type: {renderer_type}")
