"""This file is just for testing.

It lists the available mpris2 players
and prints their status.
"""

import asyncio
import pprint

from . import Mpris2Dbussy, unwrap_metadata


async def async_main():
    mpris = await Mpris2Dbussy.create()
    players = await mpris.get_players()
    print("Found players: " + ", ".join(p.name for p in players))

    for player in players:
        print()
        print(f"Report for player {player.name!r} (bus name: {player.bus_name})")
        for prop in ('PlaybackStatus', 'Volume', 'Position', 'CanControl'):
            print(f"{prop}:", await getattr(player.player, prop))
        print("Metadata:")
        pprint.pprint(unwrap_metadata(await player.player.Metadata))


loop = asyncio.get_event_loop()
loop.run_until_complete(async_main())
