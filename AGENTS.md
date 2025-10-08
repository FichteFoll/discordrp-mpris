# Project Overview

This project, `discordrp-mpris`, is a Python application that provides Discord Rich Presence based on media players that support the MPRIS D-Bus interface. It runs in the background, detects media players, and displays the currently playing media on Discord.

The application is built using Python 3.12+ and relies on the `jeepney` library for D-Bus communication and a custom `discord_rpc` library for Discord integration. The project uses `uv` for dependency management and packaging.

## Dependencies



## Building and Running

1.  **Install dependencies:**
    ```bash
    uv sync
    ```
2.  **Run the application:**
    ```bash
    uv run discordrp-mpris
    ```
3.  **Build the wheel:**
    ```bash
    uv build
    ```
*   **Logging:** The application uses the `logging` module for logging. The log level can be configured in the `config.toml` file.
