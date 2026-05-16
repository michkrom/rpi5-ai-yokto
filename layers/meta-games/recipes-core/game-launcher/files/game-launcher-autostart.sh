#!/bin/sh
# Yokto Game Launcher autostart - runs in weston-terminal after Weston starts
# This is sourced from /etc/profile.d so it runs once per login session

# Only run in Weston session with global socket
if [ -z "$WAYLAND_DISPLAY" ] && [ ! -S "/run/wayland-0" ]; then
    echo "game-launcher: no weston session, skipping" >> /tmp/game-launcher.log
    exit 0
fi

# Prevent multiple runs per session
if [ -n "$GAME_LAUNCHER_STARTED" ]; then
    echo "game-launcher: already started, skipping" >> /tmp/game-launcher.log
    exit 0
fi
export GAME_LAUNCHER_STARTED=1

# Run game-launcher in weston-terminal fullscreen
echo "game-launcher: starting weston-terminal" >> /tmp/game-launcher.log
/usr/bin/weston-terminal --fullscreen -- /usr/bin/game-launcher &