# Nyasnake

A lightweight multiplayer snake simulation with a headless engine, pluggable renderers, and a deterministic AI loop. The codebase is structured so that the game logic runs independently of the terminal UI, making it easy to extend with new renderers or smarter agents.

## Quick Start

```bash
# (Optional) create a virtualenv, then install test deps
pip install -r requirements.txt

# Run the simulation
python main.py --seed 1337

# Show available options
python main.py --help

# Run the test suite
pytest -q
```

## Command-Line Options

```
usage: main.py [-h] [--seed SEED] [--tick-interval SECONDS] [--tick-rate FPS]
               [--ai-level {easy,normal,hard}] [--interactive]
               [--log-level {DEBUG,INFO,WARNING,ERROR}] [--debug]
```

- `--seed`: deterministic random seed (defaults to `config.GAME_CONFIG.DEFAULT_SEED`).
- `--tick-interval` / `--tick-rate`: control simulation cadence in seconds or frames per second.
- `--ai-level`: selects controller presets (`easy`=all defensive, `normal`=profile defaults, `hard`=all aggressive).
- `--interactive`: enable WASD controls for snake `0`, powered by the non-blocking keyboard adapter.
- `--debug`: toggles debug overlays (currently traces spawn and path markers).

## Project Layout

```
nyasnake/
├── ai.py                  # Greedy controller + helpers
├── engine.py              # Immutable state & tick transition
├── exceptions.py          # Custom Nyasnake exception hierarchy
├── factories.py           # Factories for AI controllers and renderers
├── game.py                # Phase-based game runner, renderer & inputs
├── models.py              # Core geometry primitives (Position, Direction)
├── pathfinding.py         # Grid A* tuned for immutable snapshots
├── config.py              # Tunable constants and debug flags
├── main.py                # CLI entry point
└── tests/
    ├── test_behaviors.py  # Strategy-driven controller behaviour checks
    ├── test_evaluation.py # Engine tick, scoring and collisions
    ├── test_game_runner.py# Game loop orchestration helpers
    ├── test_input.py      # Keyboard adapter edge cases
    └── test_pathfinding.py# Pathfinding correctness & corner cases
```

## Architecture Overview

- **Engine (`engine.py`)** – Owns `GameState` and `SnakeState`, both immutable. The `advance_state` function processes simultaneous moves, resolves collisions, awards kills, and respawns food using a `random.Random` instance to guarantee reproducibility.
- **Renderer & Input (`game.py`)** – `GameRunner` now composes a `GameLoop`, `DecisionCollector`, `EventDispatcher`, and `StateHistory` to run the simulation. Renderers operate through the command pattern, while the keyboard adapter emits `MoveCommand` objects that can be replayed from history.
- **AI (`ai.py`)** – The `GreedyAIController` supplies synchronous decisions for every snake. It looks for safe moves, aims for the nearest food using the simplified A*, and falls back to a local space heuristic when no target exists. Personalities are realised via concrete strategies (`AggressiveStrategy`, `DefensiveStrategy`, `BalancedStrategy`) selected through a factory.
- **Pathfinding (`pathfinding.py`)** – A minimal A* implementation aware of immutable snapshots. It allows traversing a snake’s own tail (which frees up after the move) while respecting board bounds and other bodies.
- **Models (`models.py`)** – Contains only `Direction` and `Position` utilities to keep dependencies lean and reusable.

## Testing

The suite focuses on pure logic so tests run quickly without invoking the renderer.

```bash
pytest
```

- `test_evaluation.py` exercises scoring, food respawn, wall collisions, and head-to-head resolution via the engine.
- `test_pathfinding.py` verifies the simplified A* behaviour (straight paths, obstacles, trapped scenarios, tail traversal).
- `test_behaviors.py` ensures the strategy-driven controller produces sensible moves given food placement, obstacles, and traps.

## Extending the Project

- **Renderers**: implement the `Renderer` protocol in `game.py` and pass it to `GameRunner` (or wire it through `RendererFactory`).
- **Inputs**: subclass `InputProvider` for new input devices (gamepads, network clients, etc.) that emit `InputCommand` instances.
- **AI**: build alternative controllers that implement `decide(state)` and supply them to `GameRunner`.
- **Events**: register a custom `GameEventVisitor` to react to engine events, or tap into `StateHistory` for replays.
- **Tests**: leverage the immutable engine structures to build concise, deterministic scenarios.

## License

MIT (see `LICENSE` if provided). Feel free to remix and build your own variants.
