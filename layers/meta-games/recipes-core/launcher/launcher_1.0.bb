SUMMARY = "Yokto Launcher - Simple TUI for game selection"
DESCRIPTION = "A lightweight text-based UI to launch games and download game data"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://launcher \
           file://launcher.desktop \
           file://launcher-autostart.desktop \
           file://launcher.service \
           file://launcher-autostart.sh \
"

S = "${WORKDIR}"

RDEPENDS:${PN} = "python3-core wget weston"

inherit systemd

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${WORKDIR}/launcher ${D}${bindir}/
    install -d ${D}${datadir}/applications
    install -m 0644 ${WORKDIR}/launcher.desktop ${D}${datadir}/applications/
    install -d ${D}${datadir}/autostart
    install -m 0644 ${WORKDIR}/launcher-autostart.desktop ${D}${datadir}/autostart/
    # Install autostart script for profile.d
    install -d ${D}${sysconfdir}/profile.d
    install -m 0755 ${WORKDIR}/launcher-autostart.sh ${D}${sysconfdir}/profile.d/
    # Install systemd service for user session
    install -d ${D}${systemd_user_unitdir}
    install -m 0644 ${WORKDIR}/launcher.service ${D}${systemd_user_unitdir}/
    # Enable the service for graphical-session.target
    install -d ${D}${systemd_user_unitdir}/graphical-session.target.wants
    ln -s ../launcher.service ${D}${systemd_user_unitdir}/graphical-session.target.wants/launcher.service
}

FILES:${PN} = "${bindir}/launcher ${datadir}/applications/launcher.desktop"
FILES:${PN} += "${datadir}/autostart/launcher-autostart.desktop ${systemd_user_unitdir}/launcher.service"
FILES:${PN} += "${sysconfdir}/profile.d/launcher-autostart.sh"
FILES:${PN} += "${systemd_user_unitdir}/graphical-session.target.wants"