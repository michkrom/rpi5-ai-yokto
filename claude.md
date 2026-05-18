# Claude Notes

## Target Device Shell

**Important:** The Raspberry Pi 5 target devices run **BusyBox shell**, not bash. This means:

- Limited command options (e.g., `ps` has no `-a` flag, `head` doesn't support `-n`)
- Missing common GNU utilities like `timeout`, `pkill`
- Use POSIX-compatible commands:
  - `ls` instead of `ls -la` long format
  - `ps` without options
  - Simple pipes without GNU extensions

## Working with Targets

- Use `target_connect` to connect to RPi5 at its IP
- Use `target_exec` for running commands remotely
- For EGL testing, run `weston-simple-egl` after setting `XDG_RUNTIME_DIR` and `WAYLAND_DISPLAY`

## EGL Test Results

The spinning rainbow triangles from `weston-simple-egl` confirm EGL is working correctly on the target device.

## Doom/SDL2 Issue Investigation

**Root Cause Found:** SDL2 on the target was not built with proper EGL/Opengles support because:
1. The meta-yokto layer's `libsdl2_%.bbappend` was not being applied due to missing `conf/layer.conf`
2. The bbappend was in the wrong directory (`layers/meta-yokto` instead of `meta-yokto`)
3. Even after fixing, the layer priority was too low

**Fix Applied:**
- Updated `meta-yokto/conf/layer.conf` with `BBFILE_PRIORITY_yokto = "12"`
- Added bbappend with `EXTRA_OECMAKE += " -DSDL_OPENGLES=ON -DSDL_OPENGL=ON"` and `DEPENDS += "virtual/egl virtual/libgles2"`
- This ensures SDL2 properly supports Wayland/EGL for games like chocolate-doom

**Why quake3e works but Doom doesn't:**
- quake3e uses Vulkan renderer (`-DUSE_VULKAN=ON -DUSE_OPENGL=OFF`)
- chocolate-doom uses SDL2/OpenGL which requires EGL integration
- Vulkan bypasses the SDL2 EGL issue entirely