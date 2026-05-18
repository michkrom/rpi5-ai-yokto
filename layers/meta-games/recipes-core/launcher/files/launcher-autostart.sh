#!/bin/sh
# Yokto Launcher autostart - runs in weston-terminal after Weston starts
# This is sourced from /etc/profile.d so it runs once per login session

# Check for Wayland socket - either global or user-specific
has_socket=0
if [ -S "/run/wayland-0" ]; then
    has_socket=1
elif [ -S "/run/user/$(id -u)/wayland-0" ]; then
    has_socket=1
elif [ -S "/run/user/$(id -u)/wayland-1" ]; then
    has_socket=1
fi

# Only run in Weston session with socket
if [ $has_socket -eq 0 ]; then
    echo "launcher: no weston session, skipping" >> /tmp/launcher.log
    exit 0
fi

# Prevent multiple runs per session
if [ -n "$LAUNCHER_STARTED" ]; then
    echo "launcher: already started, skipping" >> /tmp/launcher.log
    exit 0
fi
export LAUNCHER_STARTED=1

# Run launcher in weston-terminal fullscreen
echo "launcher: starting weston-terminal" >> /tmp/launcher.log
echo "launcher: WAYLAND_DISPLAY=$WAYLAND_DISPLAY" >> /tmp/launcher.log
/usr/bin/weston-terminal --fullscreen -- /usr/bin/launcher &