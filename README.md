# Discord Rich Presence through mpris

discordrp-mpris provides Rich Presence to Discord clients
based on music or other media that you are playing
and that is exposed through the [mpris2][] D-Bus interface.
Thus, it only works on systems where D-Bus is available
and *not* on Windows.

discordrp-mpris is intended to run in the background
alongside your local Discord client
and your media player(s).
Multiple media players are supported
and the ones with active playback are prioritized.
The most recently active player will then be followed
until it is no longer playing
and a different player starts playback.

The code works for now,
but could be improved.
Notably, configuration is missing.


## Installation & Usage

Requirements:

- Python 3.6

### Recommended

- **Arch Linux**: [AUR](https://aur.archlinux.org/packages/discordrp-mpris-git/)

```sh
systemctl --user enable discordrp-mpris.service --now
```

### pipenv

Requires [pipenv][].

```sh
git clone https://github.com/FichteFoll/discordrp-mpris
cd discordrp-mpris
pipenv install

# Usage
pipenv run python -m discordrp-mpris
```

### Manually

```sh
pip install https://github.com/ldo/dbussy
pip install https://github.com/FichteFoll/discordrp-mpris

# Usage
discordrp-mpris
```


## Media Players

The following media players are known to be supported:

- [cmus][]
- [Media Player Daemon][mpd] (through [mpDris2][] - `master` branch)
- [mpv][] (through [mpv-mpris][])
- [VLC Media Player][vlc]

Icons are available for:

- Media Player Daemon
- mpv
- VLC Media Player

When no player icon is available,
the playback state is used as the large icon.

## Configuration

None currently.


<!-- Links -->

[mpris2]: https://specifications.freedesktop.org/mpris-spec/2.2/
[pipenv]: https://docs.pipenv.org/
[cmus]: https://cmus.github.io/
[mpd]: https://musicpd.org/
[mpDris2]: https://github.com/eonpatapon/mpDris2
[mpv]: https://mpv.io/
[mpv-mpris]: https://github.com/hoyon/mpv-mpris
[vlc]: https://www.videolan.org/vlc/
