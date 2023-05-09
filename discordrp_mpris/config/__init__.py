from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import cast, Any, Dict, Optional
import sys

from .types import TomlTable

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from ampris2 import PlayerInterfaces as Player

USER_CONFIG_ROOTS = ("$XDG_CONFIG_HOME", "$HOME/.config")

logger = logging.getLogger(__name__)


# TODO automatic reloading
class Config:
    _obj = object()

    def __init__(self, raw_config: TomlTable) -> None:
        self.raw_config = raw_config

    def raw_get(self, key: str, default: Any = None) -> Any:
        segments = key.split('.')  # TODO doesn't support players with "."
        base: Any = self.raw_config
        for seg in segments:
            if not isinstance(base, dict):
                logger.warning(f"Expected a dict before segment {seg!r}, got {type(base)}")
                return default
            if seg not in base:
                logger.debug(f"No value for key {key!r}; using default {default!r}")
                return default
            base = base[seg]
        logger.debug(f"Value for {key!r}: {base!r}")
        return base

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw_get(f"options.{key}", default)

    def player_get(self, player: Player, key: str, default: Any = None) -> Any:
        base = self.get(key, default)
        return self.raw_get(f"player.{player.name}.{key}", base)

    @classmethod
    def load(cls) -> Config:
        config = _load_default_file()
        if user_config := _load_user_file():
            merge_tables(config, user_config)
        return cls(config)


def merge_tables(table1: TomlTable, table2: TomlTable) -> None:
    """Recursively merge two dictionaries, modifying `table1` in-place."""
    for key, value in table2.items():
        if key in table1 and isinstance(table1[key], dict) and isinstance(value, dict):
            merge_tables(cast(TomlTable, table1[key]), value)
        else:
            table1[key] = value


def _load_default_file() -> TomlTable:
    """Load the default config file.

    We expect this file to be available at all times to provide us with defaults.
    """
    default_file = Path(__file__).parent / "config.toml"
    return _read_file(default_file)


def _load_user_file() -> Optional[TomlTable]:
    """Load the user config file, if available."""
    for pattern in USER_CONFIG_ROOTS:
        if (
            (config_root := Path(os.path.expandvars(pattern))).is_dir()
            and (user_file := config_root / "discordrp-mpris" / "config.toml").is_file()
        ):
            logging.debug(f"Loading user config: {user_file!s}")
            return _read_file(user_file)

    return None


def _read_file(path: Path) -> TomlTable:
    with path.open('rb') as f:
        return tomllib.load(f)
