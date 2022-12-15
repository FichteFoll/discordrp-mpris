import logging
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from typing import Any, Dict
from atexit import register

import pytoml

from ampris2 import PlayerInterfaces as Player

logger = logging.getLogger(__name__)

default_file = Path(__file__).parent / "config.toml"


class ConfigChangedEventHandler(FileSystemEventHandler):
    def __init__(self, load_config_func):
        super().__init__()
        self.load_config_func = load_config_func

    def on_modified(self, event):
        self.load_config_func()
        logger.debug("Modifications to config are loaded")


class Config:
    _obj = object()
    config_file = default_file

    def __init__(self, raw_config: Dict[str, Any] = None) -> None:
        self.raw_config = raw_config
        self.observer = Observer()
        self.watch = None
        self.config_handler = ConfigChangedEventHandler(self.load)

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

    def setup_reloading(self):
        self.watch = self.observer.schedule(self.config_handler, str(self.config_file))
        self.observer.start()
        register(self.observer.stop)

    def load(self):
        self._load_config()

    def check(self):
        wconf = self.raw_config
        tconf = self._load_config_from_path(default_file)
        flag = set(tconf["global"].keys()) == set(wconf["global"].keys()) and set(tconf["options"].keys()) == \
               set(wconf["options"].keys())
        return flag

    def _load_config(self):
        user_patterns = ("$XDG_CONFIG_HOME", "$HOME/.config")

        for pattern in user_patterns:
            parent = Path(os.path.expandvars(pattern))
            if parent.is_dir():
                user_file = parent / "discordrp-mpris" / "config.toml"
                if user_file.is_file():
                    logging.debug(f"Loading user config: {user_file!s}")
                    self.config_file = user_file
                    self.raw_config = self._load_config_from_path(user_file)
                    return
            self.config_file = default_file
            self.raw_config = self._load_config_from_path(default_file)

    @staticmethod
    def _load_config_from_path(path):
        with path.open() as f:
            return pytoml.load(f)
