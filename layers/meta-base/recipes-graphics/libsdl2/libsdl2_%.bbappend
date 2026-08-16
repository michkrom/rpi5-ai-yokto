# SDL2 configuration for Raspberry Pi 5
# 
# Raspberry Pi 5 uses modern DRM/KMS driver which requires SDL2's KMSDRM video driver
# for direct rendering without X11 or Wayland compositor.
#
# For wayland builds (DISTRO_FEATURES includes "wayland"), SDL automatically enables
# SDL_WAYLAND and SDL_OPENGLES via PACKAGECONFIG. We explicitly ensure KMSDRM and Gles2
# are enabled for direct DRM/KMS rendering capability.

# Enable KMSDRM and Gles2 video drivers for Raspberry Pi 5
# kmsdrm: Direct DRM/KMS rendering without X11/Wayland
# gles2: OpenGL ES 2.0 support via Mesa
PACKAGECONFIG:append = " kmsdrm gles2"

# Add dependencies for KMSDRM and Wayland video drivers
RDEPENDS:libsdl2:append = " wayland libdrm libgbm"

# Apply patch for RTLD_GLOBAL on wayland-egl and GLES libraries to fix symbol visibility
# This ensures wl_egl_window_* symbols are visible to libwayland-client
# and that GLES symbols are properly exported when loaded via dlopen()
# NOTE: required - boot/GUI does not work without it (RTLD_LOCAL hides the symbols)
FILESEXTRAPATHS:prepend := "${THISDIR}/libsdl2:"
SRC_URI:append:class-target = " file://0001-Use-RTLD_GLOBAL-for-wayland-egl.patch"

# Allow patch fuzz for this custom patch
INSANE_SKIP:append = " patch-fuzz"

# Ensure EGL and GLES2 libraries are found during build
DEPENDS += "virtual/egl virtual/libgles2 libdrm virtual/libgbm"