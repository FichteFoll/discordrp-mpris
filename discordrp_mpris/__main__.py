import asyncio
import logging
import time
from typing import Dict, Iterable, List, Optional


import ampris2
# from ampris2 import Mpris2Dbussy, PlayerInterfaces, PlaybackStatus
from discord_rpc.async import AsyncDiscordRpc, DiscordRpcError, JSON

CLIENT_ID = '435587535150907392'
PLAYER_ICONS = {'Music Player Daemon': 'mpd',
                'mpv': 'mpv',
                'VLC media player': 'vlc'}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG)

Player = ampris2.PlayerInterfaces

STATE_PRIORITY = (ampris2.PlaybackStatus.PLAYING,
                  ampris2.PlaybackStatus.PAUSED,
                  ampris2.PlaybackStatus.STOPPED)


class DiscordMpris:

    active_player: Optional[Player] = None
    last_activity: Optional[JSON] = None

    def __init__(self, mpris: ampris2.Mpris2Dbussy, discord: AsyncDiscordRpc) -> None:
        self.mpris = mpris
        self.discord = discord

    async def connect_discord(self):
        if self.discord.connected:
            return
        logger.debug("Trying to connect to Discord client...")
        while True:
            try:
                await self.discord.connect()
            except DiscordRpcError:
                logger.debug("Failed to connect to Discord client")
                await asyncio.sleep(1)
            except asyncio.streams.IncompleteReadError:
                logger.debug("Connection to Discord lost")
                await asyncio.sleep(1)
            else:
                logger.info("Connected to Discord client")
                return

    async def run(self):
        await self.connect_discord()

        while True:
            try:
                await self.tick()
            except (ConnectionResetError, BrokenPipeError):
                logger.info("Connection to Discord client lost. Reconnecting...")
                await self.connect_discord()
            await asyncio.sleep(10)  # TODO make configurable

    async def tick(self) -> None:
        player = await self.find_active_player()
        if not player:
            if self.last_activity:
                await self.discord.clear_activity()
                self.last_activity = None
            return
        # store for future prioritization
        if not self.active_player or self.active_player.name != player.name:
            logger.info(f"Selected player bus {player.name!r}")
        self.active_player = player

        activity: JSON = {}
        metadata, position, identity, state = \
            await asyncio.gather(
                player.player.Metadata,
                player.player.Position,
                player.root.Identity,
                player.player.PlaybackStatus,
            )
        metadata = ampris2.unwrap_metadata(metadata)
        length = metadata.get('mpris:length', 0)

        replacements = self.build_replacements(player, metadata)
        replacements['position'] = self.format_timestamp(position)
        replacements['length'] = self.format_timestamp(length)
        replacements['player'] = identity
        replacements['state'] = state

        # TODO pref
        activity['details'] = self.format_details("{title} by {artist}", replacements)

        # set state and timestamps
        activity['timestamps'] = {}
        if state == ampris2.PlaybackStatus.PLAYING:
            start_time = int(time.time() - position / 1e6)
            activity['timestamps']['start'] = start_time
            # end_time = start_time + (length / 1e6)
            # activity['timestamps']['end'] = end_time
            activity['state'] = self.format_details("{state} [{length}]", replacements)
        elif state == ampris2.PlaybackStatus.PAUSED:
            activity['state'] = self.format_details("{state} [{position}/{length}]", replacements)
        else:
            activity['state'] = self.format_details("{state}", replacements)

        # set icons and hover texts
        if identity in PLAYER_ICONS:
            activity['assets'] = {'large_text': identity,
                                  'large_image': PLAYER_ICONS[identity],
                                  'small_image': state.lower(),
                                  'small_text': state}
        else:
            activity['assets'] = {'large_text': f"{identity} ({state})",
                                  'large_image': state.lower()}

        if activity != self.last_activity:
            await self.discord.set_activity(activity)
            self.last_activity = activity
        else:
            logger.debug("Not sending activity because it didn't change")

    async def find_active_player(self) -> Optional[Player]:
        active_player = self.active_player
        players = await self.mpris.get_players()

        # refresh active player (in case it restarted or sth)
        if active_player:
            for p in players:
                if p.name == self.active_player.name:
                    active_player = p
                    break
            else:
                logging.info(f"Player {p.name!r} lost")
                active_player = None

        groups = await self.group_players(players)
        if logger.isEnabledFor(logging.DEBUG):
            for state, group in zip(STATE_PRIORITY, groups):
                logger.debug("%s: %s", state, ", ".join(p.name for p in group))

        # Prioritize last active player per group,
        # but don't check stopped players.
        # We only want a stopped player
        # if it was the active one before.
        for group in groups[:2]:
            for p in group:
                if p is active_player:
                    return p
            else:
                if group:
                    # just pick a random one
                    return p

        return active_player  # no playing or paused player found

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
            state = ampris2.PlaybackStatus(await p.player.PlaybackStatus)
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
    def format_details(template: str, replacements: Dict[str, str]) -> str:
        return template.format(**replacements)


async def main_async():
    loop = asyncio.get_event_loop()
    # this should generally succeed, so do it first
    mpris = await ampris2.Mpris2Dbussy.create(loop=loop)

    async with AsyncDiscordRpc.for_platform(CLIENT_ID) as discord:
        instance = DiscordMpris(mpris, discord)
        await instance.run()


def main():
    # discord =
    loop = asyncio.get_event_loop()
    main_task = loop.create_task(main_async())
    try:
        loop.run_until_complete(main_task)
    # except KeyboardInterrupt:
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
            raise


if __name__ == '__main__':
    main()
