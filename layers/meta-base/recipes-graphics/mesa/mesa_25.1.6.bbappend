# Fix COMPATIBLE_MACHINE for mesa 25.1.6 from meta-raspberrypi
# The recipe has "^rpi$" which doesn't match "raspberrypi5"
# Allow both rpi and raspberrypi5 machines
COMPATIBLE_MACHINE .= "|raspberrypi5|^rpi\\d*$"

# Mesa 25 has a condition in src/meson.build that only builds the 'dril' target
# (which creates DRI driver symlinks) when with_glx == 'dri' or with_platform_x11 or with_platform_xcb.
# For Wayland-only builds with GLX disabled, the DRI symlinks (vc4_dri.so, v3d_dri.so, etc.) 
# are not created, causing EGL initialization to fail with "DRI driver not found" errors.
#
# Fix: Create DRI symlinks manually for KMSRO-based drivers (vc4, v3d)
do_install:append() {
    # Check if gallium megadriver exists but dri directory doesn't
    if [ -f ${D}${libdir}/libgallium-25.1.6.so ] && [ ! -d ${D}${libdir}/dri ]; then
        mkdir -p ${D}${libdir}/dri
        # Create DRI driver symlinks for vc4/v3d (KMSRO-based drivers)
        ln -sf ../libgallium-25.1.6.so ${D}${libdir}/dri/vc4_dri.so
        ln -sf ../libgallium-25.1.6.so ${D}${libdir}/dri/v3d_dri.so
    fi
}