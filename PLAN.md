# Migration and Refactoring Plan

## References

- `jeepney` documentation: https://jeepney.readthedocs.io/en/latest/
- MPRIS D-Bus documentation: https://specifications.freedesktop.org/mpris-spec/latest/
- `trackma` reference implementation: https://raw.githubusercontent.com/z411/trackma/refs/heads/master/trackma/tracker/mpris.py

## Plan

1.  **Update Python Version Requirement:**
    *   In `pyproject.toml`, change `requires-python` from `>=3.8` to `>=3.12`.

2.  **Update Dependencies:**
    *   Add `jeepney` to `pyproject.toml`.
    *   Remove `dbussy` and `ravel` from `pyproject.toml`.
    *   Remove `tomli` as it is included in the standard library since Python 3.11.
    *   Run `uv sync` to update the `uv.lock` file.

3.  **Restructure and Refactor `ampris2`:**
    *   Rename the `ampris2` directory to `mpris`.
    *   Inside `mpris`, create the following files to modularize the D-Bus logic:
        *   `connection.py`: Handles connecting to the D-Bus session bus using `jeepney`.
        *   `player.py`: Defines a `Player` class to manage individual player state and interactions, similar to the `trackma` example.
        *   `watcher.py`: Implements the reactive logic to watch for `NameOwnerChanged` and `PropertiesChanged` signals, inspired by the `trackma` example.
        *   `__init__.py`: Exposes the public API of the new `mpris` module.

4.  **Update `discordrp_mpris/__main__.py` for Reactive Flow:**
    *   Remove all usage of the old `Mpris2Dbussy` class.
    *   Integrate the new `mpris` module. The main loop in `DiscordMpris.run` will no longer poll for players. Instead, it will be event-driven.
    *   Implement new methods in the `DiscordMpris` class (e.g., `on_player_added`, `on_player_removed`, `on_playback_status_changed`, `on_metadata_changed`) that will be called by the `mpris.watcher`.

5.  **Remove the old `ampris2` module:**
    *   Once the new implementation is in place and working, the `ampris2` module can be removed.

6.  **Update GEMINI.md and pyproject.toml:**
    * Update the `GEMINI.md` and `pyproject.toml` files with the changes to the current environment.
