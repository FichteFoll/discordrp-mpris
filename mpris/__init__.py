"""A library for controlling MPRIS-enabled media players."""

__version__ = "0.1.0"

from .player import Player, PlaybackStatus
from .watcher import Watcher

__all__ = [
    "Player",
    "PlaybackStatus",
    "Watcher",
]
