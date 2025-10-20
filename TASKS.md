# Project Tasks

- [x] Wire `SnakeStrategy` personalities into decision-making in `ai.py:29-88` and extend `tests/test_behaviors.py` to cover the divergent behaviours.
- [x] Make the CLI `--ai-level` flag in `main.py:16-74` actually select different controller presets (or remove the flag) and document the options in `README.md`.
- [ ] Document the new controller override and event listener hooks added to `game.py:33-252` in the README, including a short usage snippet.
- [ ] Prototype web backend (FastAPI/WebSocket) that wraps `GameRunner` and streams JSON frames to validate the service-facing architecture.
