import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import pytoml

from ampris2 import PlayerInterfaces as Player

logger = logging.getLogger(__name__)

default_file = Path(__file__).parent / "config.toml"


# TODO automatic reloading
class Config:
    _obj = object()

    def __init__(self, raw_config: Dict[str, Any]) -> None:
        self.raw_config = raw_config

    def raw_get(self, key: str, default: Any = None) -> Any:
        segments = key.split('.')
        base: Any = self.raw_config
        for seg in segments:
            if seg not in base:  # this assumes a valid "mapping path"
                logger.debug(f"No value for key {key!r}")
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
    def load(cls) -> 'Config':
        with default_file.open() as f:
            config = pytoml.load(f)
        user_config = cls._load_user_config()
        if user_config:
            config.update(user_config)
        return Config(config)

    @staticmethod
    def _load_user_config() -> Optional[Dict[str, Any]]:
        user_patterns = ("$XDG_CONFIG_HOME", "$HOME/.config")
        user_file = None

        for pattern in user_patterns:
            parent = Path(os.path.expandvars(pattern))
            if parent.is_dir():
                user_file = parent / "discordrp-mpris" / "config.toml"
                if user_file.is_file():
                    logging.debug(f"Loading user config: {user_file!s}")
                    with user_file.open() as f:
                        return pytoml.load(f)

        return None
