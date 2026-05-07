#!/bin/sh
# Yokto Game Launcher - runs once per session
# Check if we're in a Weston session and launcher hasn't run yet

if [ -n "$WAYLAND_DISPLAY" ] && [ -z "$GAME_LAUNCHER_SHOWN" ]; then
    export GAME_LAUNCHER_SHOWN=1
    # Give Weston a moment to settle
    sleep 2
    # Run launcher in background, logging output
    /usr/bin/game-launcher 2>&1 | logger -t game-launcher &
fi