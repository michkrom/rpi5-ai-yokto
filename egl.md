# EGL Issues with Chocolate Doom on Raspberry Pi 5 - Final Solution

## Problem
Chocolate Doom failed with "Error creating window for video startup: EGL not initialized" on Raspberry Pi 5 with Wayland-only configuration.

## Root Cause
1. **SDL_WINDOW_OPENGL flag required**: SDL2's Wayland backend only initializes EGL when this flag is present during window creation
2. **Missing GLES library path**: SDL2 dynamically loads libGLESv2 but couldn't find the correct library on Yocto systems

## Solution Applied

### 1. Chocolate Doom Patch
Added `SDL_WINDOW_OPENGL` flag to window creation in `i_video.c`:
```c
window_flags |= SDL_WINDOW_OPENGL;  // Needed for EGL initialization on Wayland
```

### 2. SDL Environment Variables
Set globally in `/etc/profile.d/sdl2-profile.sh`:
```bash
export SDL_VIDEODRIVER=wayland
export SDL_RENDER_DRIVER=opengles2
export SDL_VIDEO_GL_DRIVER=/usr/lib/libGLESv2.so.2  # Critical for Yocto
```

### 3. Wayland Socket Detection
Auto-detected Wayland socket in profile script:
```bash
# Find active XDG runtime directory
for sock in /run/user/*/wayland-*; do
    if [ -S "$sock" ]; then
        export WAYLAND_DISPLAY=$(basename "$sock")
        export XDG_RUNTIME_DIR=$(dirname $(dirname "$sock"))
        break
    fi
done
```

### 4. SDL2 Renderer Test Update
Added `SDL_WINDOW_OPENGL` flag to test for proper EGL initialization testing.

## Result
✅ **Chocolate Doom now launches and displays correctly on Raspberry Pi 5**

All tests work:
- egl-test (direct EGL) - Shows graphics
- sdl2-renderer-test - Shows graphics  
- chocolate-doom - Runs successfully