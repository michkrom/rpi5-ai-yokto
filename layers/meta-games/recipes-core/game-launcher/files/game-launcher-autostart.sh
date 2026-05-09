#!/bin/sh
# Yokto Game Launcher autostart
# Runs on Weston startup, offering options to download or launch games
# Supported games: Quake III (q3e), Doom (chocolate-doom), Warfork

# Check if Weston is running and WAYLAND_DISPLAY is set
if [ -z "$WAYLAND_DISPLAY" ]; then
    # Try to find a Wayland display
    for sock in /run/user/*/wayland-0; do
        if [ -S "$sock" ]; then
            export WAYLAND_DISPLAY=$(basename "$sock")
            break
        fi
    done
fi

# Run the game launcher
if [ -n "$WAYLAND_DISPLAY" ] || [ -S "/run/wayland-0" ]; then
    /usr/bin/game-launcher 2>&1 | logger -t game-launcher &
fi

# Log that the autostart occurred
logger -t game-launcher "Game launcher started on Weston session"