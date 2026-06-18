#!/bin/bash
# Alternative launcher wrapper that works with weston-terminal --shell
# This replaces the shell in weston-terminal with direct launcher execution

cd /home/weston
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-1

# Run the Python launcher
exec /usr/bin/python3 /usr/bin/launcher