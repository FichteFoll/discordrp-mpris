# Discord Rich Presence through mpris

discordrp-mpris provides Rich Presence to Discord clients
based on music or other media that you are playing
and that is exposed through the [mpris2][] dbus interface.

It is intended to run in the background
alongside your local Discord client
and the media player.
Multiple media players are supported
and the ones with active playback are prioritized.
The most recently active player will then be followed
until it is no longer playing
and a different player starts playback.

The code works for now,
but could be improved.
Notably, configuration is missing.


## Installation

Requirements:

- Python 3.6
- pipenv

```sh
git clone https://github.com/FichteFoll/discordrp-mpris
cd discordrp-mpris
pipenv install
```


## Usage

```sh
pipenv run python -m discordrp-mpris
```
