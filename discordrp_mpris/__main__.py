import asyncio
import logging
import re
import sys
import time
from textwrap import shorten
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Union

from ampris2 import Mpris2Dbussy, PlaybackStatus, PlayerInterfaces as Player, unwrap_metadata
import dbussy
from discord_rpc.async_ import (AsyncDiscordRpc, DiscordRpcError, JSON,
                                exceptions as async_exceptions)

from .config import Config

CLIENT_ID = '435587535150907392'
PLAYER_ICONS = {
    # Maps player identity name to icon name
    # https://discord.com/developers/applications/435587535150907392/rich-presence/assets
    'Clementine': 'clementine',
    'Media Player Classic Qute Theater': 'mpc-qt',
    'mpv': 'mpv',
    'Music Player Daemon': 'mpd',
    'VLC media player': 'vlc',
    'SMPlayer': 'smplayer',
    'Lollypop': 'lollypop',
    'Mozilla Firefox': 'firefox',
}
DEFAULT_LOG_LEVEL = logging.WARNING

logger = logging.getLogger(__name__)
logging.basicConfig(
    style='{',
    level=DEFAULT_LOG_LEVEL,
    format="{asctime} | {levelname:<8} | {message} [{name}]",
)

STATE_PRIORITY = [
    PlaybackStatus.PLAYING,
    PlaybackStatus.PAUSED,
    PlaybackStatus.STOPPED,
    PlaybackStatus.UNKNOWN,
]

# Maximum allowed characters of Rich Presence's "details" field
DETAILS_MAX_CHARS = 128

# Relative weight for shortening when details exceeds max length
weigth_map: Dict[str, int] = DefaultDict(
    lambda: 1,
    title=4,
    xesam_title=4,
    artist=2,
    album=2,
    xesam_album=2,
)


class DiscordMpris:

    active_player: Optional[Player] = None
    last_activity: Optional[JSON] = None

    def __init__(self, mpris: Mpris2Dbussy, discord: AsyncDiscordRpc, config: Config,
                 ) -> None:
        self.mpris = mpris
        self.discord = discord
        self.config = config

    async def connect_discord(self) -> None:
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
        metadata, state = \
            await asyncio.gather(
                player.player.Metadata,  # type: ignore
                player.player.PlaybackStatus,  # type: ignore
            )
        # Some players (like Firefox) don't support the required Position property
        position: Optional[Union[int, float]]
        try:
            position = await player.player.Position  # type: ignore
        except dbussy.DBusError as e:
            position = None
            logger.debug("Failed to retrieve position", exc_info=e)
        metadata = unwrap_metadata(metadata)
        logger.debug(f"Metadata: {metadata}")
        length = metadata.get('mpris:length', 0)

        # position should already be an int, but some players (smplayer) return a float
        replacements = self.build_replacements(player, metadata, position, length, state)

        # TODO make format configurable
        if replacements['artist']:
            # details_fmt = "{artist} - {title}"
            details_fmt = "{title}\nby {artist}"
        else:
            details_fmt = "{title}"
        details = self.format_details(details_fmt, replacements)

        activity['details'] = details

        # set state and timestamps
        activity['timestamps'] = {}
        if length and position is not None:
            if state == PlaybackStatus.PLAYING:
                show_time = self.config.player_get(player, 'show_time', 'elapsed')
                start_time = int(time.time() - position / 1e6)
                if show_time == 'elapsed':
                    activity['timestamps']['start'] = start_time
                elif show_time == 'remaining':
                    end_time = start_time + (length / 1e6)
                    activity['timestamps']['end'] = end_time
                activity['state'] = self.format_details("{state} [{length}]", replacements)
            elif state == PlaybackStatus.PAUSED:
                activity['state'] = self.format_details("{state} [{position}/{length}]",
                                                        replacements)
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
                if p.bus_name == active_player.bus_name:
                    active_player = p
                    break
            else:
                logger.info(f"Player {active_player.bus_name!r} lost")
                self.active_player = active_player = None

        groups = await self.group_players(players)
        if logger.isEnabledFor(logging.DEBUG):
            debug_list = [(state, ", ".join(p.bus_name for p in groups[state]))
                          for state in STATE_PRIORITY]
            logger.debug(f"found players: {debug_list}")

        # Prioritize last active player per group,
        # but only check playing or paused.
        for state in STATE_PRIORITY[:2]:
            group = groups[state]
            candidates: List[Player] = []
            for p in group:
                if p is active_player:
                    candidates.insert(0, p)
                else:
                    candidates.append(p)

            for player in group:
                if (
                    not self.config.player_get(player, "ignore", False)
                    and (state == PlaybackStatus.PLAYING
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

    @classmethod
    def build_replacements(
        cls,
        player: Player,
        metadata: Dict[str, Any],
        position: Optional[Union[int, float]],
        length: Optional[int],
        state: PlaybackStatus,
    ) -> Dict[str, Any]:
        replacements = metadata.copy()

        # aggregate artist and albumArtist fields
        for key in ('artist', 'albumArtist'):
            source = metadata.get(f'xesam:{key}', ())
            if isinstance(source, str):  # In case the server doesn't follow mpris specs
                replacements[key] = source
            else:
                replacements[key] = " & ".join(source)
        # shorthands
        replacements['title'] = metadata.get('xesam:title', "")
        replacements['album'] = metadata.get('xesam:album', "")

        # other data
        replacements['position'] = \
            cls.format_timestamp(int(position)) if position is not None else ''
        replacements['length'] = cls.format_timestamp(length)
        replacements['player'] = player.name
        replacements['state'] = state

        # replace invalid ident char
        replacements = {key.replace(':', '_'): val for key, val in replacements.items()}

        return replacements

    @staticmethod
    async def group_players(players: Iterable[Player]
                            ) -> Dict[PlaybackStatus, List[Player]]:
        groups: Dict[PlaybackStatus, List[Player]] = {state: [] for state in PlaybackStatus}
        for p in players:
            try:
                state = PlaybackStatus(await p.player.PlaybackStatus)  # type: ignore
            except ValueError:
                state = PlaybackStatus.UNKNOWN
            groups[state].append(p)

        return groups

    @staticmethod
    def format_timestamp(microsecs: Optional[int]) -> Optional[str]:
        if microsecs is None:
            return None
        secs = microsecs // int(1e6)
        mins, secs = divmod(secs, 60)
        hours, mins = divmod(mins, 60)
        string = f"{mins:d}:{secs:02d}"
        if hours > 0:
            string = f"{hours:d}:{mins:02d}:{secs:02d}"
        return string

    @staticmethod
    def format_details(template: str, replacements: Dict[str, Any]) -> str:
        # Assumes that there are no numeric characters in the template.
        details = template.format_map(replacements)

        if len(details) > DETAILS_MAX_CHARS:
            # Insert null character between replacements
            # so that consecutive replacements don't result in a big number.
            details_with_weigths = template.replace("}{", "}\0{").format_map(weigth_map)
            print(f"{details_with_weigths=}")
            total_weight = sum(map(float, re.findall(r"[\d.]+", details_with_weigths)))
            print(f"{total_weight=}")
            num_fixed_chars = len(re.sub(r"[\d.\0]+", '', details_with_weigths))
            print(f"{num_fixed_chars=}")
            factor = (DETAILS_MAX_CHARS - num_fixed_chars) / total_weight
            print(f"{factor=}")
            weighted_replacements = {
                key: shorten(str(value), int(weigth_map[key] * factor), placeholder='…')
                for key, value in replacements.items()
            }
            details = template.format_map(weighted_replacements)

        return details


async def main_async(loop: asyncio.AbstractEventLoop):
    config = Config.load()
    # TODO validate?
    configure_logging(config)

    mpris = await Mpris2Dbussy.create(loop=loop)
    async with AsyncDiscordRpc.for_platform(CLIENT_ID) as discord:
        instance = DiscordMpris(mpris, discord, config)
        return await instance.run()


def main() -> int:
    loop = asyncio.new_event_loop()
    main_task = loop.create_task(main_async(loop))
    try:
        return loop.run_until_complete(main_task)
    except BaseException as e:
        main_task.cancel()
        wait_task = asyncio.wait_for(main_task, 5)
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


def configure_logging(config: Config) -> None:
    log_level = logging.WARNING
    if config.raw_get('global.debug', False):
        log_level_name = 'DEBUG'
    else:
        log_level_name = config.raw_get('global.log_level')
    if log_level_name and log_level_name.isupper():
        log_level = getattr(logging, log_level_name, log_level)

    # set level of root logger
    logging.getLogger().setLevel(log_level)

    logger.debug(f"Config: {config.raw_config}")


if __name__ == '__main__':
    sys.exit(main())
