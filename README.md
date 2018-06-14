# Discord Rich Presence through mpris

| User Modal          | Popout Modal          |
| ------------------- | --------------------- |
| ![][img-user-modal] | ![][img-popout-modal] |

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

### Manual

```sh
pip install https://github.com/FichteFoll/discordrp-mpris

# Usage
discordrp-mpris
```

You might want to use `pip install --user`.


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

Configuration may be provided in a `config.toml` file
using the [TOML][] format.
It may be located in `$XDG_CONFIG_HOME/discordrp-mpris`
or `$HOME/.config/discordrp-mpris`.

For available options, see the [default `config.toml`][default-config].


<!-- Resources -->

[img-user-modal]: https://user-images.githubusercontent.com/931051/39368449-e0da4afa-4a39-11e8-8909-2d3b2383ad9f.png
[img-popout-modal]: https://user-images.githubusercontent.com/931051/39368450-e0fb03da-4a39-11e8-8fc3-d6910f097243.png

<!-- Links -->

[mpris2]: https://specifications.freedesktop.org/mpris-spec/2.2/
[pipenv]: https://docs.pipenv.org/
[cmus]: https://cmus.github.io/
[mpd]: https://musicpd.org/
[mpDris2]: https://github.com/eonpatapon/mpDris2
[mpv]: https://mpv.io/
[mpv-mpris]: https://github.com/hoyon/mpv-mpris
[vlc]: https://www.videolan.org/vlc/
[TOML]: https://github.com/toml-lang/toml
[default-config]: config/config.toml
