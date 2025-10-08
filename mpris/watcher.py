"""Implements the reactive logic to watch for NameOwnerChanged and PropertiesChanged signals."""
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from jeepney.bus_messages import message_bus, MatchRule
from jeepney.io.blocking import DBusConnection
from jeepney.wrappers import unwrap_msg

from .connection import open_main_connection
from .player import (
    BUS_NAMESPACE,
    IFACE_MPRIS_PLAYER,
    IFACE_PROPERTIES,
    PATH_MPRIS,
    Player,
)


class Watcher:
    """Watches for player events and calls the appropriate callbacks."""

    def __init__(self, on_player_added: Callable[[Player], None], on_player_removed: Callable[[Player], None], on_playback_status_changed: Callable[[Player], None], on_metadata_changed: Callable[[Player], None]):
        self.conn = open_main_connection()
        self.players: Dict[str, Player] = {}
        self.on_player_added = on_player_added
        self.on_player_removed = on_player_removed
        self.on_playback_status_changed = on_playback_status_changed
        self.on_metadata_changed = on_metadata_changed

    def watch(self) -> None:
        """Block forever and watch for player events."""
        bus_proxy = message_bus.proxy(self.conn)

        # Add match rules for NameOwnerChanged and PropertiesChanged
        rule_noc = MatchRule(
            type="signal",
            sender=message_bus.bus_name,
            interface=message_bus.interface,
            member="NameOwnerChanged",
            path=message_bus.object_path,
        )
        rule_noc.add_arg_condition(0, BUS_NAMESPACE, kind="namespace")
        bus_proxy.AddMatch(rule_noc)

        rule_pc = MatchRule(
            type="signal",
            interface=IFACE_PROPERTIES,
            member="PropertiesChanged",
            path=PATH_MPRIS,
        )
        rule_pc.add_arg_condition(0, IFACE_MPRIS_PLAYER)
        bus_proxy.AddMatch(rule_pc)

        logging.info("Watching for media players...")

        # Initial scan for players
        for wellknown_name, unique_name in self._list_players():
            self._add_player(wellknown_name, unique_name)

        while True:
            msg = self.conn.receive()
            if msg.member == "NameOwnerChanged":
                (wellknown_name, old_owner, new_owner) = unwrap_msg(msg)

                if new_owner and not old_owner:
                    self._add_player(wellknown_name, new_owner)
                elif old_owner and not new_owner:
                    self._remove_player(old_owner)
            elif msg.member == "PropertiesChanged":
                if not msg.sender:
                    continue
                player = self.players.get(msg.sender)
                if not player:
                    continue

                _iface, changed, _invalidated = msg.body
                if "PlaybackStatus" in changed:
                    self.on_playback_status_changed(player)
                if "Metadata" in changed:
                    self.on_metadata_changed(player)

    def _list_players(self) -> List[Tuple[str, str]]:
        """List all players on the bus."""
        bus_proxy = message_bus.proxy(self.conn)
        names: List[str] = bus_proxy.ListNames()
        mpris_names = [name for name in names if name.startswith(BUS_NAMESPACE)]

        return [
            (name, bus_proxy.GetNameOwner(name))
            for name in mpris_names
        ]

    def _add_player(self, wellknown_name: str, unique_name: str) -> None:
        """Add a player to the list of players."""
        if unique_name in self.players:
            return

        logging.info(f"Player added: {wellknown_name}")
        player = Player(wellknown_name, unique_name, self.conn)
        self.players[unique_name] = player
        self.on_player_added(player)

    def _remove_player(self, unique_name: str) -> None:
        """Remove a player from the list of players."""
        if unique_name not in self.players:
            return

        player = self.players.pop(unique_name)
        logging.info(f"Player removed: {player.wellknown_name}")
        self.on_player_removed(player)
