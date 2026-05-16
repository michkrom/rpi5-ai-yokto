# Add wayland dependency for SDL2 - the Wayland video driver needs
# libwayland-egl for wl_egl_window_* functions when rendering
RDEPENDS:libsdl2:append = " wayland"

# Force SDL2 to properly link/USE EGL - the Wayland driver requires this
# Without this, SDL2 tries to dlopen() EGL at runtime which can fail
EXTRA_OECMAKE += " -DSDL_OPENGLES=ON -DSDL_OPENGL=ON"

# Ensure EGL and GLES2 libraries are found during build
DEPENDS += "virtual/egl virtual/libgles2"

# Apply patch to fix wayland-egl symbol visibility
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI:append = " file://0001-Use-RTLD_GLOBAL-for-wayland-egl.patch"