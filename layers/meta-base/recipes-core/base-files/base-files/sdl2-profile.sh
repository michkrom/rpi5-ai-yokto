# SDL2 environment for Raspberry Pi 5 Wayland
# Sets the video driver and renderer for SDL2 applications
# This is sourced by /etc/profile.d/ for all login shells

# Tell SDL2 to use Wayland video backend
export SDL_VIDEODRIVER=wayland

# Force the renderer to use OpenGL ES 2 (maps cleanly over Wayland EGL)
export SDL_RENDER_DRIVER=opengles2

# Force SDL2 to load the correct GLES library path
# This is critical for Yocto-based systems where libGLESv2.so.2 is in /usr/lib/
export SDL_VIDEO_GL_DRIVER=/usr/lib/libGLESv2.so.2

# Set Wayland display defaults (respects running compositor sessions)
# Only set if WAYLAND_DISPLAY socket exists
if [ -z "$WAYLAND_DISPLAY" ]; then
    for sock in /run/user/*/wayland-1 /run/user/*/wayland-0; do
        if [ -S "$sock" ]; then
            export WAYLAND_DISPLAY=$(basename "$sock")
            export XDG_RUNTIME_DIR=$(dirname $(dirname "$sock"))
            break
        fi
    done
fi