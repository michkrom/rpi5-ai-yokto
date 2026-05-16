#!/bin/sh
# Yokto Game Launcher autostart
# Runs on Weston startup via profile.d, offering options to download or launch games

# Only run in Weston session
if [ -z "$WAYLAND_DISPLAY" ] && [ ! -S "/run/wayland-0" ]; then
    exit 0
fi

# Prevent multiple runs
if [ -n "$GAME_LAUNCHER_STARTED" ]; then
    exit 0
fi
export GAME_LAUNCHER_STARTED=1

# Run game-launcher in weston-terminal fullscreen
exec /usr/bin/weston-terminal --fullscreen -- /usr/bin/game-launcher