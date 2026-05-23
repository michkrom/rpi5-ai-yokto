# SDL2 environment for Raspberry Pi 5 Wayland
# Sets the video driver and renderer for SDL2 applications
# This is sourced by /etc/profile.d/ for all login shells

# Tell SDL2 to use Wayland video backend
export SDL_VIDEODRIVER=wayland

# Force the renderer to use OpenGL ES 2 (maps cleanly over Wayland EGL)
export SDL_RENDER_DRIVER=opengles2

# Set Wayland display defaults (can be overridden by session)
# Only set if not already set (respects running compositor sessions)
if [ -z "$WAYLAND_DISPLAY" ]; then
    export WAYLAND_DISPLAY=wayland-0
fi
if [ -z "$XDG_RUNTIME_DIR" ]; then
    export XDG_RUNTIME_DIR=/run/user/$(id -u 2>/dev/null || echo 0)
fi