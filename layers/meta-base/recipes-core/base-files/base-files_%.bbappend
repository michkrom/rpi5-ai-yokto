# Add SDL2/Wayland environment configuration for Raspberry Pi 5
# This sets up the SDL2 video driver and renderer environment for all shells

FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

SRC_URI:append = " file://sdl2-profile.sh"

do_install:append() {
    # Install profile script for shell login
    install -d ${D}${sysconfdir}/profile.d
    install -m 0644 ${WORKDIR}/sdl2-profile.sh ${D}${sysconfdir}/profile.d/
}