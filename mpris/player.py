from __future__ import annotations

"""Defines a Player class to manage individual player state and interactions."""
import os
import urllib.parse
from dataclasses import dataclass
from enum import Enum
from typing import Union, Dict, Any

from jeepney.io.blocking import DBusConnection
from jeepney import Properties, DBusAddress
from jeepney.wrappers import MessageGenerator


BUS_NAMESPACE = "org.mpris.MediaPlayer2"
PATH_MPRIS = "/org/mpris/MediaPlayer2"
IFACE_PROPERTIES = "org.freedesktop.DBus.Properties"
IFACE_MPRIS = "org.mpris.MediaPlayer2"
IFACE_MPRIS_PLAYER = IFACE_MPRIS + ".Player"


class PlaybackStatus(str, Enum):
    PLAYING = "Playing"
    PAUSED = "Paused"
    STOPPED = "Stopped"


class Player(MessageGenerator):
    """A proxy object for a remote media player."""

    interface = IFACE_MPRIS_PLAYER

    def __init__(
        self,
        connection: DBusConnection,
        bus_name: str,
        obj_path: str = PATH_MPRIS,
    ) -> None:
        """Initialize the player."""
        super().__init__(obj_path=obj_path, bus_name=bus_name)
        self.connection = connection
        self.properties = Properties(self)

    def get_property(self, name: str) -> Any:
        """Get a property from the player."""
        msg = self.properties.get(name)
        reply = self.connection.send_and_get_reply(msg)
        return reply.body[0][1]

    @property
    def playback_status(self) -> PlaybackStatus:
        """The current playback status of the player."""
        return PlaybackStatus(self.get_property("PlaybackStatus"))

    @property
    def metadata(self) -> Dict[str, Any]:
        """The metadata of the currently playing track."""
        return {
            key: value[1]
            for key, value in self.get_property("Metadata").items()
        }