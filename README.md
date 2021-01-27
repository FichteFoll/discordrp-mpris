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

This project is in *beta* stage.


## Installation & Usage

Requirements:

- Python 3.6

### Recommended

- **Arch Linux**: [AUR](https://aur.archlinux.org/packages/discordrp-mpris-git/)

```sh
systemctl --user enable discordrp-mpris.service --now
```

### Manual

```sh
pip install https://github.com/FichteFoll/discordrp-mpris

# Usage
discordrp-mpris
```

You might also want to use `pip install --user`.

### pipenv

Requires [pipenv][].

```sh
git clone https://github.com/FichteFoll/discordrp-mpris
cd discordrp-mpris
pipenv install

# Usage
pipenv run python -m discordrp-mpris
```


## Media Players

The following media players are known to be supported:

- [Clementine][]
- [Strawberry][]
- [cmus][]
- KDE Plasma integration through:
    - [Chrome addon][kde-chrome]
    - [FireFox addon][kde-firefox]
- [Lollypop][]
- [Media Player Classic Qute Theater][mpc-qt] (newer than 18.03 or 2018-06-20)
- [Media Player Daemon][mpd] (through [mpDris2][] - `master` branch)
- [mpv][] (through [mpv-mpris][])
- [SMPlayer][]
- [VLC Media Player][vlc]

Icons are available for:

- Clementine
- Lollypop
- Media Player Daemon
- Media Player Classic Qute Theater
- mpv
- SMPlayer
- VLC Media Player

When no player icon is available,
the playback state is used as the large icon.

The following players are **not** supported:

- Spotify
  (conflicts with its own Rich Presence, #4)
- [mps-youtube][]
  (doesn't implement introspectable DBus properties,
  mps-youtube/mps-youtube#839)


## Configuration

Configuration may be provided in a `config.toml` file
using the [TOML][] format
and located in the folders `$XDG_CONFIG_HOME/discordrp-mpris`
or `$HOME/.config/discordrp-mpris`.

For available options, see the [default `config.toml`][default-config].


<!-- Resources -->

[img-user-modal]: https://user-images.githubusercontent.com/931051/39368449-e0da4afa-4a39-11e8-8909-2d3b2383ad9f.png
[img-popout-modal]: https://user-images.githubusercontent.com/931051/39368450-e0fb03da-4a39-11e8-8fc3-d6910f097243.png

<!-- Links -->

[mpris2]: https://specifications.freedesktop.org/mpris-spec/2.2/
[pipenv]: https://docs.pipenv.org/
[Clementine]: https://www.clementine-player.org/
[Strawberry]: https://www.strawberrymusicplayer.org/
[cmus]: https://cmus.github.io/
[kde-chrome]: https://chrome.google.com/webstore/detail/plasma-integration/cimiefiiaegbelhefglklhhakcgmhkai
[kde-firefox]: https://addons.mozilla.org/en-US/firefox/addon/plasma-integration/
[Lollypop]: https://wiki.gnome.org/Apps/Lollypop
[mpc-qt]: https://github.com/cmdrkotori/mpc-qt
[mpd]: https://musicpd.org/
[mpDris2]: https://github.com/eonpatapon/mpDris2
[mpv]: https://mpv.io/
[mpv-mpris]: https://github.com/hoyon/mpv-mpris
[vlc]: https://www.videolan.org/vlc/
[mps-youtube]: https://github.com/mps-youtube/mps-youtube
[SMPlayer]: https://www.smplayer.info/
[TOML]: https://github.com/toml-lang/toml
[default-config]: discordrp_mpris/config/config.toml
