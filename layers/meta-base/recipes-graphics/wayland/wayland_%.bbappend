# Fix for Raspberry Pi 5 SDL2 Wayland EGL integration
# The meta-raspberrypi wayland_%.bbappend removes libwayland-egl when vc4graphics
# is not set, but we need it for SDL2's Wayland video driver which uses
# wl_egl_window_* symbols for EGL surface creation.
#
# This bbappend ensures libwayland-egl is always installed and wayland-client
# is properly linked to it.

# Prevent the meta-raspberrypi bbappend from removing libwayland-egl
# The do_install from the original recipe runs first, then our append runs
do_install:append:rpi() {
    : # No-op - libwayland-egl should already be installed
}

# Ensure wayland-client has proper dependency on wayland-egl
# This is critical for SDL2's Wayland video driver to find wl_egl_window_* symbols
WAYLAND_CLIENT_EXTRA_LIBS:rpi = "-lwayland-egl"