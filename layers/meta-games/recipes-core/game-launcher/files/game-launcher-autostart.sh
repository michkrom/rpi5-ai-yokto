#!/bin/sh
# Yokto Game Launcher autostart
# Runs on Weston startup, offering options to download or launch games
# Supported games: Quake III (q3e), Doom (chocolate-doom), Warfork

# Run in a way that doesn't block weston startup
(sleep 3 && game-launcher 2>&1 | logger -t game-launcher) &

# Log that the autostart occurred
logger -t game-launcher "Game launcher started on Weston session"