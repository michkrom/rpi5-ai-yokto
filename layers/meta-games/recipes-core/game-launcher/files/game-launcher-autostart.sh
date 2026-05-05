#!/bin/sh
# Yokto Game Launcher autostart
# Always runs on Weston startup, offering options to download or launch games

# Run in a way that doesn't block weston startup
(sleep 3 && game-launcher 2>&1 | logger -t game-launcher) &