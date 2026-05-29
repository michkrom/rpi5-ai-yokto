#!/bin/bash
# Chocolate Doom wrapper for Wayland compatibility
# Sets necessary SDL2 hints before launching

export SDL_VIDEODRIVER=wayland
export SDL_RENDER_DRIVER=opengles2

# Disable fullscreen by default (windowed mode works better with Wayland)
exec /usr/bin/chocolate-doom "$@"