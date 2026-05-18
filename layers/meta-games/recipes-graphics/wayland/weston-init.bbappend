SUMMARY = "Startup script and systemd unit file for the Weston Wayland compositor"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

SRC_URI += "file://weston-socket.sh"

# Override the do_install to use our fixed weston-socket.sh
do_install:append() {
    # Install fixed weston-socket.sh with user-specific socket detection
    install -D -p -m0755 ${WORKDIR}/weston-socket.sh ${D}${sysconfdir}/profile.d/weston-socket.sh
}