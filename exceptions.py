"""
Custom exceptions for the Nyasnake game engine.
"""


class NyasnakeError(Exception):
    """Base exception for all Nyasnake-specific errors."""
    pass


class ConfigurationError(NyasnakeError):
    """Raised when there's an error in game configuration."""
    pass


class TerminalError(NyasnakeError):
    """Raised when terminal operations fail."""
    pass


class GameStateError(NyasnakeError):
    """Raised when there's an error in game state operations."""
    pass


class AIDecisionError(NyasnakeError):
    """Raised when AI decision making fails."""
    pass
