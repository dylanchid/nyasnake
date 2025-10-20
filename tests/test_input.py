from __future__ import annotations

import types

import pytest

import game
from game import KeyboardInput
from models import Direction


class _StubStdin:
    def __init__(self, is_tty: bool, fileno_callable=None):
        self._is_tty = is_tty
        self._fileno_callable = fileno_callable

    def isatty(self) -> bool:
        return self._is_tty

    def fileno(self):
        if self._fileno_callable is None:
            raise AssertionError("fileno should not be called")
        return self._fileno_callable()

    def read(self, size: int) -> str:
        return ""


def test_keyboard_input_skips_terminal_setup_when_not_tty(monkeypatch):
    stdin = _StubStdin(is_tty=False)
    monkeypatch.setattr(game.sys, "stdin", stdin)

    keyboard = KeyboardInput({"w": (0, Direction.UP)})

    assert getattr(keyboard, "_fd") is None


def test_keyboard_input_handles_fileno_errors(monkeypatch):
    def raise_value_error():
        raise ValueError("no fd")

    stdin = _StubStdin(is_tty=True, fileno_callable=raise_value_error)
    monkeypatch.setattr(game.sys, "stdin", stdin)

    keyboard = KeyboardInput({"w": (0, Direction.UP)})

    assert getattr(keyboard, "_fd") is None
