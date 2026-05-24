# EGL Issues with Chocolate Doom on Raspberry Pi 5

## Problem Summary

Chocolate Doom fails with error **"Error creating window for video startup: EGL not initialized"** when running on the Yocto-built image, despite working in local builds.

## Root Cause Analysis

### 1. EGL Initialization Failure Point
From the error, SDL2's Wayland video driver fails during `SDL_CreateWindow()`:
- Weston is running (`wayland-0` socket exists)
- `WAYLAND_DISPLAY` and `XDG_RUNTIME_DIR` are properly set
- Error: **"EGL not initialized"** - EGL context creation failed

### 2. Mesa Build Configuration (25.1.6)
From build logs:
- **gallium-drivers**: `["softpipe", "vc4", "v3d", "zink", "virgl"]` - ✓ vc4/v3d built
- **platforms**: `["wayland"]` - Only Wayland, no X11
- **glx**: `"disabled"` - No X11 DRI drivers built (expected for Wayland-only)
- **egl**: `"enabled"` - EGL support enabled

### 3. Missing DRI Drivers - THE ROOT CAUSE
**CRITICAL**: The `/usr/lib/dri/` directory was **MISSING** on the target!

**Why this happens:**
In Mesa 25.1.6, the `dril` target (which creates DRI driver symlinks like `vc4_dri.so` and `v3d_dri.so`) is only built when:
```meson
if with_glx == 'dri' or with_platform_x11 or with_platform_xcb
    subdir('gallium/targets/dril')
endif
```

For a Wayland-only build with `glx=disabled`, these conditions are all false, so no DRI symlinks are created!

**The fix:** Added `do_install:append()` in `mesa_25.1.6.bbappend` to create the symlinks manually.

### 4. SDL2 Linker Issue
From target check:
```
ldd /usr/lib/libSDL2-2.0.so.0.3000.1 | grep -i egl
```
Returns empty - **SDL2 is NOT linked to EGL**!

This is actually expected behavior for SDL2 - it uses `dlopen()` to load EGL dynamically when needed. The real issue was the missing DRI drivers.

### 5. **wl_egl_window Symbol Visibility Issue**

**Problem:** SDL2's Wayland video driver dynamically loads `libwayland-egl.so` using `dlopen()` with `RTLD_LOCAL` flag. This hides the `wl_egl_window_*` symbols from other libraries.

**Code Path:**
1. SDL2 Wayland driver calls `SDL_LoadObject("libwayland-egl.so.1")`
2. `SDL_LoadObject()` uses `dlopen(..., RTLD_NOW | RTLD_LOCAL)` by default
3. `wl_egl_window_create()` and related functions are loaded but symbols are hidden
4. When Mesa EGL driver tries to access `wl_egl_window_*` symbols, they're not found

**SDL2 Code Analysis (from SDL_waylanddyn.c):**
```c
static waylanddynlib waylandlibs[] = {
    { NULL, SDL_VIDEO_DRIVER_WAYLAND_DYNAMIC },      // libwayland-client
    { NULL, SDL_VIDEO_DRIVER_WAYLAND_DYNAMIC_EGL },  // libwayland-egl
    // ...
};
```

**The Fix:** Created patch `0001-Use-RTLD_GLOBAL-for-wayland-egl.patch`:
```c
// In SDL_sysloadso.c - SDL_LoadObject()
/* RTLD_GLOBAL for wayland-egl */
if (SDL_strstr(sofile, "wayland-egl")) {
    handle = dlopen(sofile, RTLD_NOW | RTLD_GLOBAL);
} else {
    handle = dlopen(sofile, RTLD_NOW | RTLD_LOCAL);
}
```

## Fixes Applied

### Fix 1: Mesa DRI Driver Symlinks ✅
Created `layers/meta-base/recipes-graphics/mesa/mesa_25.1.6.bbappend`:
```bash
do_install:append() {
    if [ -f ${D}${libdir}/libgallium-25.1.6.so ] && [ ! -d ${D}${libdir}/dri ]; then
        mkdir -p ${D}${libdir}/dri
        ln -sf ../libgallium-25.1.6.so ${D}${libdir}/dri/vc4_dri.so
        ln -sf ../libgallium-25.1.6.so ${D}${libdir}/dri/v3d_dri.so
    fi
}
```

### Fix 2: SDL2 RTLD_GLOBAL Patch ✅
Updated `layers/meta-base/recipes-graphics/libsdl2/libsdl2_%.bbappend`:
```bash
FILESEXTRAPATHS:prepend := "${THISDIR}/libsdl2:"
SRC_URI:append:class-target = " file://0001-Use-RTLD_GLOBAL-for-wayland-egl.patch"
```

## Patch File Details

**Location:** `layers/meta-base/recipes-graphics/libsdl2/libsdl2/0001-Use-RTLD_GLOBAL-for-wayland-egl.patch`

**Contents:**
```diff
Use RTLD_GLOBAL for wayland-egl to avoid symbol visibility issues.
libwayland-client needs wl_egl_window_* symbols from libwayland-egl.
Without RTLD_GLOBAL, these symbols remain hidden when loaded via dlopen().

Upstream-Status: Pending

--- a/src/loadso/dlopen/SDL_sysloadso.c
+++ b/src/loadso/dlopen/SDL_sysloadso.c
@@ -46,7 +46,12 @@ void *SDL_LoadObject(const char *sofile)
     }
 #endif
 
-    handle = dlopen(sofile, RTLD_NOW | RTLD_LOCAL);
+    /* RTLD_GLOBAL for wayland-egl */
+    if (SDL_strstr(sofile, "wayland-egl")) {
+        handle = dlopen(sofile, RTLD_NOW | RTLD_GLOBAL);
+    } else {
+        handle = dlopen(sofile, RTLD_NOW | RTLD_LOCAL);
+    }
     loaderror = dlerror();
     if (!handle) {
         SDL_SetError("Failed loading %s: %s", sofile, loaderror);
```

## Test Results - May 21, 2026

### SDL2 EGL Test Run on Target

**Test binary compiled and copied to target:**
- Binary: `/tmp/sdl2-egl-test` (ARM64, cross-compiled via bitbake)
- SDL2 binary SHA256 verified - patch IS applied

**Error observed:**
```
Window could not be created! SDL_Error: Could not initialize OpenGL / GLES library
```

**LD_DEBUG=libs reveals the real issue:**
```
/usr/lib/libwayland-client.so.0: error: symbol lookup error: undefined symbol: wl_egl_window_create (fatal)
/usr/lib/libwayland-client.so.0: error: symbol lookup error: undefined symbol: wl_egl_window_destroy (fatal)
/usr/lib/libwayland-client.so.0: error: symbol lookup error: undefined symbol: wl_egl_window_resize (fatal)
...
```

**Key finding:** The `wl_egl_window_*` symbols are marked GLOBAL in libwayland-egl.so.1:
```
readelf -Ws /usr/lib/libwayland-egl.so.1 | grep wl_egl
     9: 0000000000000880    32 FUNC    GLOBAL DEFAULT   12 wl_egl_window_get_attached_size
    10: 0000000000000840    56 FUNC    GLOBAL DEFAULT   12 wl_egl_window_destroy
    11: 00000000000007a0    48 FUNC    GLOBAL DEFAULT   12 wl_egl_window_resize
    12: 00000000000007d0   108 FUNC    GLOBAL DEFAULT   12 wl_egl_window_create
```

**But wait - why is libwayland-client looking for wl_egl_window symbols?**
- This should not be happening - wl_egl_window is for libwayland-egl, not libwayland-client
- This suggests weston (the compositor) was built with wrong configuration or there's a version mismatch

### Local Build Works

- chocolate-doom built locally in `~/git/chocolate-doom` works fine
- This confirms the issue is specific to the Yocto build configuration

### Root Cause Identified - May 21, 2026

**THE PROBLEM IS IN meta-raspberrypi's wayland_%.bbappend!**

```
# File: layers/meta-raspberrypi/recipes-graphics/wayland/wayland_%.bbappend
# until fully tested, prefer `libwayland-egl` provided by `userland` instead of `wayland` when not using vc4graphics
do_install:append:rpi () {
    if [ "${@bb.utils.contains("MACHINE_FEATURES", "vc4graphics", "1", "0", d)}" = "0" ]; then
        rm -f ${D}${libdir}/libwayland-egl*
        rm -f ${D}${libdir}/pkgconfig/wayland-egl.pc
    fi
}
```

**What this means:**
- If `MACHINE_FEATURES` does NOT contain `vc4graphics`, the wayland recipe REMOVES `libwayland-egl`
- This was intended for older Pi models that use `userland` for EGL
- **BUT:** For Pi5 with Mesa 25.1.6, we NEED `libwayland-egl` from wayland package!

**Check rpi-base.inc:**
```
MACHINE_FEATURES += "apm usbhost keyboard vfat ext2 screen touchscreen alsa bluetooth wifi sdio ${@bb.utils.contains('DISABLE_VC4GRAPHICS', '1', '', 'vc4graphics', d)}"
```

`vc4graphics` should be there by default unless `DISABLE_VC4GRAPHICS=1`.

**Verification needed:**
1. Check if DISABLE_VC4GRAPHICS is set somewhere
2. Verify what MACHINE_FEATURES actual value is in the build

## Current Status - May 21, 2026

### Files Updated
1. ✅ `layers/meta-games/recipes-support/sdl2-test/sdl2-egl-test.bb` - Fixed paths and DEPENDS
2. ✅ `layers/meta-games/recipes-support/sdl2-test/files/sdl2-egl-test.c` - Main test program
3. ✅ `egl-test.c` in project root - Lower-level EGL test without SDL2

### BREAKTHROUGH - Lower-level EGL Test PASSED! ✅

```
=== EGL Wayland Test ===
Step 1: Connecting to Wayland display...OK (fd=3)
Step 2: Getting compositor interface...OK
Step 3: Creating Wayland surface...OK
Step 4: Creating EGL window (640x480)...OK
Step 5: Initializing EGL...OK (EGL 1.5)
Step 6: Choosing EGL config...OK (1 configs found)
Step 7: Creating EGL context (GLES2)...OK
Step 8: Creating EGL surface...OK
Step 9: Making context current...OK
Step 10: Clearing screen with blue color...OK
=== ALL TESTS PASSED ===
```

**This proves:**
- ✅ Mesa 25.1.6 EGL works correctly
- ✅ Wayland integration works
- ✅ DRI drivers and libgallium are correct
- ✅ weston compositor is properly running

**THE PROBLEM IS IN SDL2'S WAYLAND VIDEO DRIVER!**

## Summary & Next Steps

### Verified Working ✅
- Mesa 25.1.6 EGL initialization
- Wayland compositor (weston) 
- Direct EGL/Wayland integration (egl-test passes)
- DRI driver symlinks
- libwayland-egl symbols

### SDL2 RTLD_GLOBAL Patch Status ✅ **PATCH APPLIED**
**Verified May 23, 2026:**
- Build library MD5: `546c83e56ace6e232c286543da167a32`
- Target library MD5: `546c83e56ace6e232c286543da167a32`
- **PATCH MATCHES** - the RTLD_GLOBAL fix IS applied to the target

### Remaining Issue ❌ **PATCH IS NOT THE ROOT CAUSE**
Despite the RTLD_GLOBAL patch being correctly applied, SDL2's Wayland video driver still fails to initialize EGL. This means:
1. The symbol visibility issue was NOT the root cause, OR
2. There's another underlying problem masking the fix

### Next Investigation Needed
1. Check if weston version/configuration is the issue
2. Verify mesa EGL driver loading on the target
3. Test if SDL2's wayland-egl loading path works at all
4. Check for any libinput/evdev issues in the weston environment

### Root Cause (FINAL)
The `libwayland-client.so.0` on the running target (Mar 9 build) had incorrect undefined symbol references to `wl_egl_window_*` functions. This was caused by the `meta-raspberrypi wayland_%.bbappend` which removes `libwayland-egl` when `vc4graphics` is not in MACHINE_FEATURES, but the wayland-client library was still somehow built with those symbol dependencies.

The freshly rebuilt wayland image (May 21) has **correct** libraries where `libwayland-client.so.0` does NOT have `wl_egl_window_*` references.

### Solution Applied
1. Created `layers/meta-base/recipes-graphics/wayland/wayland_%.bbappend` to ensure libwayland-egl is installed for Pi5
2. SDL2 RTLD_GLOBAL patch is correctly applied and compiled

### Action Required
**Flash the newly built image** (`image-wayland.wic.bz2`) to the SD card. The current image has outdated libraries.

### Key Insight: Quake3 Works, Chocolate Doom Fails
- **Quake3 (q3e)**: Uses Vulkan → ✅ Works
- **Chocolate Doom**: Uses SDL2/EGL → ❌ Fails

This proves the GPU, mesa, and Vulkan work correctly. The issue is specifically in **SDL2's EGL initialization path**.

### SDL2 EGL Load Sequence
Looking at `SDL_egl.c`, SDL2 loads libraries in this order:
1. `libGLESv2.so.2` (or `libbrcmGLESv2.so` on RPi) - OpenGL ES library
2. `libEGL.so.1` - EGL library

The error "Could not initialize OpenGL / GLES library" occurs when step 1 fails to load.

### Current RTLD_GLOBAL Patch Limitation
The current patch only applies `RTLD_GLOBAL` to:
- `wayland-client`
- `wayland-egl`
- `wayland-cursor`

But it does NOT apply to `libGLESv2.so.2`. On Raspberry Pi 5, this library may have dependencies that need symbols from wayland-egl.

### Potential Fix
The patch should also apply `RTLD_GLOBAL` to GLES libraries, or we need to ensure the library loading order is correct.

### Why the RTLD_GLOBAL Fix May Not Be Enough

Looking at SDL_egl.c line 485, the error "Could not initialize OpenGL / GLES library" occurs when `SDL_LoadObject(path)` fails for `libGLESv2.so.2`.

This can fail if:
1. The library file doesn't exist
2. A dependency of the library fails to load

On the old Mar 9 target, `libGLESv2.so.2` likely:
1. Doesn't exist (not installed)
2. Or links to wrong version of libgallium
3. Or has symbol version mismatches

### Verify After Flashing
After flashing the new image, verify:
```bash
# On target after flash:
ls -la /usr/lib/libGLESv2* /usr/lib/libgallium*
# Should show:
# libGLESv2.so.2 -> libGLESv2.so.2.0.0
# libgallium-25.1.6.so (for DRI drivers)
```

If these libraries exist and the problem persists, the issue is deeper - possibly in how SDL2's dynamic loading interacts with the Mesa GLES implementation.

### Latest Status (May 23, 2026) - TARGET RUNNING CURRENT BUILD
- **Target is running the current build** (May 21 games build based on kernel 6.12.25)
- **weston 13.0.1** is installed and running
- **libwayland-egl.so.1.22.0** has correct wl_egl_window symbols (GLOBAL visibility)
- **SDL2 RTLD_GLOBAL patch** is correctly applied (MD5 verified)
- **libGLESv2.so.2** exists and links to libgallium-25.1.6.so

**YET: Chocolate Doom still fails with "EGL not initialized"**

This confirms the RTLD_GLOBAL fix alone is NOT sufficient. The problem lies deeper in SDL2's EGL initialization logic.

### Next Steps
1. ✅ Added `egl-test` and `sdl2-egl-test` to games image (`kas/games.yml`)
2. Need to rebuild and flash new image
3. Run `egl-test` directly (bypasses SDL2, tests raw EGL/Wayland)
4. Run `sdl2-egl-test` (minimal SDL2 test)

### Debug Plan
After rebuilding:
```bash
# Test 1: Direct EGL (should work - already proven)
/usr/bin/egl-test

# Test 2: SDL2 EGL (likely to fail - isolates SDL2 issue)
/usr/bin/sdl2-egl-test
```

### Hypothesis: SDL2 GLES Library Loading
The error "Could not initialize OpenGL / GLES library" comes from `SDL_egl.c` line 485 when `libGLESv2.so.2` fails to load. Current ideas:
1. SDL2 isn't finding the right GLES library path
2. RTLD_GLOBAL needs to apply to GLES libraries too (not just wayland-*)
3. The order of library loading matters

### FIX APPLIED: Extend RTLD_GLOBAL to GLES Libraries
Updated the SDL2 patch to also use `RTLD_GLOBAL` when loading:
- `GLESv2` - OpenGL ES 2.x library  
- `GLESv1_CM` - OpenGL ES 1.x compatibility library
- `brcmGLES` - Raspberry Pi legacy GLES libraries

This ensures symbols from wayland-egl are visible when MESAGLES loads.

## Additional SDL2 Configuration Fixes - May 23, 2026

### SDL2 PACKAGECONFIG Updates
Updated `layers/meta-base/recipes-graphics/libsdl2/libsdl2_%.bbappend` to explicitly ensure both `kmsdrm` and `gles2` are enabled:

```bash
# Enable KMSDRM and Gles2 video drivers for Raspberry Pi 5
# kmsdrm: Direct DRM/KMS rendering without X11/Wayland
# gles2: OpenGL ES 2.0 support via Mesa
PACKAGECONFIG:append = " kmsdrm gles2"
```

The `gles2` PACKAGECONFIG is automatically added when `DISTRO_FEATURES` includes `wayland`, but we explicitly add both to ensure correct SDL2 build configuration.

### Global Runtime Environment Setup
Created `layers/meta-base/recipes-core/base-files/base-files_%.bbappend` to set SDL2 environment variables globally:

**File:** `layers/meta-base/recipes-core/base-files/base-files/sdl2-profile.sh`
```bash
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
```

### Testing Before Building
After flashing the image, test these environment settings manually on the target:

```bash
# Verify environment is set correctly
echo $SDL_VIDEODRIVER
echo $SDL_RENDER_DRIVER
echo $WAYLAND_DISPLAY
echo $XDG_RUNTIME_DIR

# Run SDL2 EGL test
/usr/bin/sdl2-egl-test

# Run chocolate-doom with verbose logging
export SDL_LOG_PRIORITY=verbose
chocolate-doom
```

### Verifying Libraries on Target
```bash
# Check SDL2 has Wayland support compiled in
ldd /usr/lib/libSDL2-2.0.so.0 | grep wayland

# Verify DRI drivers exist
ls -la /usr/lib/dri/

# Check libGLESv2 is properly linked
ls -la /usr/lib/libGLESv2*

# Verify libwayland-egl symbols
readelf -Ws /usr/lib/libwayland-egl.so.1 | grep wl_egl
```

### Vulkan Compatibility
The SDL2 configuration maintains Vulkan support as `vulkan` is in the `PACKAGECONFIG ??=` default list and is automatically added when `DISTRO_FEATURES` includes `vulkan`. The `kmsdrm` and `gles2` additions do not conflict with Vulkan.

### User Groups Configuration
Added `EXTRA_USERS` in `kas/base.yml` to add the `pi` user to `video` and `render` groups:

```yaml
users: |
  # Add pi user to video and render groups for SDL2/EGL access
  EXTRA_USERS = "usermod -a -G video,render pi;"
```

This ensures SDL2 has permission to open `/dev/dri/card0` and `/dev/dri/renderD128` for EGL initialization.

---

## May 23, 2026 - Additional Fixes Implemented

### 1. EGL Test Program Created ✅
**File:** `layers/meta-games/recipes-support/sdl2-test/egl-test.bb`

A standalone EGL test that bypasses SDL2 entirely, proving EGL/Wayland/Mesa works correctly:

```c
// Creates colorful animated display using raw EGL + Wayland + GLES2
// - Connects to Wayland compositor via registry
// - Creates EGLSurface with wl_egl_window
// - Renders animated shader-based pattern
// - Runs for 5 seconds then exits
```

**Build recipe:**
```bash
SUMMARY = "EGL Wayland visual test"
LICENSE = "MIT"
DEPENDS = "virtual/egl wayland virtual/libgles2"
```

### 2. SDL2 EGL Test Updated ✅
The existing `sdl2-egl-test` recipe at `layers/meta-games/recipes-support/sdl2-test/sdl2-egl-test.bb` was updated with correct DEPENDS.

### 3. Launcher Updated - Shows Hostname/IP ✅
**File:** `layers/meta-games/recipes-core/launcher/files/launcher`

Added network info display at startup:
```python
def get_network_info():
    """Get hostname and IP address info"""
    info = {"hostname": "unknown", "ip": "unknown", "connected": False}
    info["hostname"] = os.uname().nodename
    # ... IP detection via ip -4 addr ...
    return info
```

### 4. Launcher Service Fixed - Single Shot ✅
**File:** `layers/meta-games/recipes-core/launcher/files/launcher.service`

Changed from `Type=simple` to `Type=oneshot` to run launcher once per session in weston-terminal fullscreen.

**File:** `layers/meta-games/recipes-core/launcher/files/launcher-autostart.sh`

Changed background execution (`&`) to `exec` for proper session behavior.

### Build Status - May 23, 2026
- **Build completed successfully** - all 7291 tasks passed
- **SWU file generated** - `yokto-games-swu.swu` in deploy directory
- **WIC image generated** - `image-wayland.wic.bz2` (ready to flash)

### Next Steps
1. Flash the new image: `invoke flash --device /dev/sdb --games`
2. Boot target and run tests:
   ```bash
   # Direct EGL test (bypasses SDL2)
   /usr/bin/egl-test
   
   # SDL2 EGL test (minimal SDL2)
   /usr/bin/sdl2-egl-test
   
   # Full game test
   /usr/bin/launcher
   ```