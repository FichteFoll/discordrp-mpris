v0.3.0 (2021-01-27)
-------------------

* Add missing pytoml dependency (#9)
* Fix compatibility with Python 3.8
* Add config for the log level and default to 'WARNING'
* Add support for Discord installed via Snap or Flatpak (#17)
* Add icons for SMPlayer and Lollypop (#7, #15)
* Be more lenient with the mpris2 interface to support SMPlayer (#7)
* Catch more exceptions


v0.2.2 (2018-09-09)
-------------------

* Fix compatibility with Python 3.7


v0.2.1 (2018-06-20)
-------------------

* Added icons for players: Clementine, mpc-qt
* Packaging fixes
* Catch and log Discord errors
* Add fallback for mpris servers not correctly following mpris spec


v0.2.0 (2018-06-15)
-------------------

* Added (player-specific) configuration capabilities and options for:
  - showing players in paused or stopped state
  - ignoring players completely
  - showing elapsed, remaining or no time
* Fixed a few uncaught exceptions
* Now doesn't crash when mps-youtube is running
* Better compatibility with Spotify's own Rich Presence
  (by ignoring it by default)


v0.1.1 (2018-04-28)
-------------------

* Bugfixes


v0.1.0 (2018-04-27)
-------------------

* Initial release
