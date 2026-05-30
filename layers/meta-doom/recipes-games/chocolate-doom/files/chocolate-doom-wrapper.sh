#!/bin/sh
# Chocolate Doom wrapper for Wayland compatibility
# Sets necessary SDL2 hints before launching

# Set SDL video driver
export SDL_VIDEODRIVER=wayland
export SDL_RENDER_DRIVER=opengles2

# Set Wayland runtime directory
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-1

# Force SDL to use the correct GLES library path
export SDL_VIDEO_GL_DRIVER=/usr/lib/libGLESv2.so.2

# Force windowed mode - fullscreen doesn't work well with Wayland/EGL in chocolate-doom
exec /usr/bin/chocolate-doom -nofullscreen -window "$@"