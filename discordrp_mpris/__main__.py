import asyncio
import logging
import sys
import time
from typing import Dict, Iterable, List, Optional

import ampris2
import dbussy
from discord_rpc.async import (AsyncDiscordRpc, DiscordRpcError, JSON,
                               exceptions as async_exceptions)

from .config import Config

CLIENT_ID = '435587535150907392'
PLAYER_ICONS = {'Music Player Daemon': 'mpd',
                'mpv': 'mpv',
                'VLC media player': 'vlc'}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

Player = ampris2.PlayerInterfaces  # type alias

STATE_PRIORITY = (ampris2.PlaybackStatus.PLAYING,
                  ampris2.PlaybackStatus.PAUSED,
                  ampris2.PlaybackStatus.STOPPED)


class DiscordMpris:

    active_player: Optional[Player] = None
    last_activity: Optional[JSON] = None

    def __init__(self, mpris: ampris2.Mpris2Dbussy, discord: AsyncDiscordRpc, config: Config,
                 ) -> None:
        self.mpris = mpris
        self.discord = discord
        self.config = config

    async def connect_discord(self):
        if self.discord.connected:
            return
        logger.debug("Trying to connect to Discord client...")
        while True:
            try:
                await self.discord.connect()
            except DiscordRpcError:
                logger.debug("Failed to connect to Discord client")
            except async_exceptions:
                logger.debug("Connection to Discord lost")
            else:
                logger.info("Connected to Discord client")
                return
            await asyncio.sleep(self.config.raw_get('global.reconnect_wait', 1))

    async def run(self) -> int:
        await self.connect_discord()

        while True:
            try:
                await self.tick()

            except async_exceptions as e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Connection error during tick", exc_info=e)
                logger.info("Connection to Discord client lost. Reconnecting...")
                await self.connect_discord()

            except dbussy.DBusError as e:
                if e.name == "org.freedesktop.DBus.Error.ServiceUnknown":
                    # bus probably terminated during tick
                    continue
                logger.exception("Unknown DBusError encountered during tick", exc_info=e)
                return 1  # TODO for now, this is unrecoverable

            await asyncio.sleep(self.config.raw_get('global.poll_interval', 5))

    async def tick(self) -> None:
        player = await self.find_active_player()
        if not player:
            if self.active_player:
                logger.info(f"Player {self.active_player.bus_name!r} unselected")
            if self.last_activity:
                await self.discord.clear_activity()
                self.last_activity = None
            self.active_player = None
            return
        # store for future prioritization
        if not self.active_player or self.active_player.bus_name != player.bus_name:
            logger.info(f"Selected player bus {player.bus_name!r}")
        self.active_player = player

        activity: JSON = {}
        metadata, position, state = \
            await asyncio.gather(
                player.player.Metadata,  # type: ignore
                player.player.Position,  # type: ignore
                player.player.PlaybackStatus,  # type: ignore
            )
        metadata = ampris2.unwrap_metadata(metadata)
        logger.debug(f"Metadata: {metadata}")
        length = metadata.get('mpris:length', 0)

        replacements = self.build_replacements(player, metadata)
        replacements['position'] = self.format_timestamp(position)
        replacements['length'] = self.format_timestamp(length)
        replacements['player'] = player.name
        replacements['state'] = state

        # TODO pref
        if replacements['artist']:
            # details_fmt = "{artist} - {title}"
            details_fmt = "{title}\nby {artist}"
        else:
            details_fmt = "{title}"
        activity['details'] = self.format_details(details_fmt, replacements)

        # set state and timestamps
        activity['timestamps'] = {}
        if state == ampris2.PlaybackStatus.PLAYING:
            show_time = self.config.player_get(player, 'show_time', 'elapsed')
            start_time = int(time.time() - position / 1e6)
            if show_time == 'elapsed':
                activity['timestamps']['start'] = start_time
            elif show_time == 'remaining':
                end_time = start_time + (length / 1e6)
                activity['timestamps']['end'] = end_time
            activity['state'] = self.format_details("{state} [{length}]", replacements)
        elif state == ampris2.PlaybackStatus.PAUSED:
            activity['state'] = self.format_details("{state} [{position}/{length}]", replacements)
        else:
            activity['state'] = self.format_details("{state}", replacements)

        # set icons and hover texts
        if player.name in PLAYER_ICONS:
            activity['assets'] = {'large_text': player.name,
                                  'large_image': PLAYER_ICONS[player.name],
                                  'small_image': state.lower(),
                                  'small_text': state}
        else:
            activity['assets'] = {'large_text': f"{player.name} ({state})",
                                  'large_image': state.lower()}

        if activity != self.last_activity:
            op_recv, result = await self.discord.set_activity(activity)
            if result['evt'] == 'ERROR':
                logger.error(f"Error setting activity: {result['data']['message']}")
            self.last_activity = activity
        else:
            logger.debug("Not sending activity because it didn't change")

    async def find_active_player(self) -> Optional[Player]:
        active_player = self.active_player
        players = await self.mpris.get_players()

        # refresh active player (in case it restarted or sth)
        if active_player:
            for p in players:
                if p.bus_name == self.active_player.bus_name:
                    active_player = p
                    break
            else:
                logger.info(f"Player {active_player.bus_name!r} lost")
                self.active_player = active_player = None

        groups = await self.group_players(players)
        if logger.isEnabledFor(logging.DEBUG):
            debug_list = [(state, ", ".join(p.bus_name for p in group))
                          for state, group in zip(STATE_PRIORITY, groups)]
            logger.debug(f"found players: {debug_list}")

        # Prioritize last active player per group,
        # but don't check stopped players.
        # We only want a stopped player
        # if it was the active one before.
        for state, group in zip(STATE_PRIORITY, groups[:2]):
            candidates: List[Player] = []
            for p in group:
                if p is active_player:
                    candidates.insert(0, p)
                else:
                    candidates.append(p)

            for player in group:
                if (
                    not self.config.player_get(player, "ignore", False)
                    and (state == ampris2.PlaybackStatus.PLAYING
                         or self.config.player_get(player, 'show_paused', True))
                ):
                    return player

        # no playing or paused player found
        if active_player and self.config.player_get(active_player, 'show_stopped', False):
            return active_player
        else:
            return None

    def _player_not_ignored(self, player: Player) -> bool:
        return (not self.config.player_get(player, "ignore", False))

    def build_replacements(self, player: Player, metadata) -> Dict[str, Optional[str]]:
        replacements = metadata.copy()

        # aggregate artist and albumArtist fields
        for key in ('artist', 'albumArtist'):
            source = metadata.get(f'xesam:{key}', ())
            replacements[key] = " & ".join(source)
        # shorthands
        replacements['title'] = metadata.get('xesam:title', "")
        replacements['album'] = metadata.get('xesam:album', "")

        # replace invalid indent char
        for key in replacements:
            if ':' in key:
                replacements[key.replace(':', '_')] = replacements[key]
                del replacements[key]

        return replacements

    @staticmethod
    async def group_players(players: Iterable[Player]
                            ) -> List[List[ampris2.PlayerInterfaces]]:
        groups: List[List[ampris2.PlayerInterfaces]] = [[], [], []]
        for p in players:
            state = ampris2.PlaybackStatus(await p.player.PlaybackStatus)  # type: ignore
            i = STATE_PRIORITY.index(state)
            groups[i].append(p)

        return groups

    @staticmethod
    def format_timestamp(microsecs: Optional[int]) -> Optional[str]:
        if microsecs is None:
            return None
        secs = microsecs // int(1e6)
        mins = secs // 60
        hours = mins // 60
        string = f"{mins % 60:d}:{secs % 60:02d}"
        if hours > 0:
            string = f"{hours:d}:{mins % 60:02d}:{secs % 60:02d}"
        return string

    @staticmethod
    def format_details(template: str, replacements: Dict[str, Optional[str]]) -> str:
        return template.format(**replacements)


async def main_async(loop: asyncio.AbstractEventLoop):
    config = Config.load()
    # TODO validate?
    if config.raw_get('global.debug', False):
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug(f"Config: {config.raw_config}")

    mpris = await ampris2.Mpris2Dbussy.create(loop=loop)
    async with AsyncDiscordRpc.for_platform(CLIENT_ID) as discord:
        instance = DiscordMpris(mpris, discord, config)
        return await instance.run()


def main() -> int:
    loop = asyncio.get_event_loop()
    main_task = loop.create_task(main_async(loop))
    try:
        return loop.run_until_complete(main_task)
    except BaseException as e:
        main_task.cancel()
        wait_task = asyncio.wait_for(main_task, 5, loop=loop)
        try:
            loop.run_until_complete(wait_task)
        except asyncio.CancelledError:
            pass
        except asyncio.TimeoutError:
            logger.error("Task didn't terminate within the set timeout")

        if isinstance(e, Exception):
            logger.exception("Unknown exception", exc_info=e)
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
