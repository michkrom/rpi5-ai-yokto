SUMMARY = "Yokto Launcher - Simple TUI for game selection"
DESCRIPTION = "A lightweight text-based UI to launch games and download game data"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://launcher \
           file://launcher-run \
           file://launcher.service \
           file://launcher-wrapper.sh \
           file://launcher.desktop \
"

S = "${WORKDIR}"

RDEPENDS:${PN} = "python3-core wget weston bash"

inherit systemd

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${WORKDIR}/launcher ${D}${bindir}/
    install -m 0755 ${WORKDIR}/launcher-run ${D}${bindir}/
    install -m 0755 ${WORKDIR}/launcher-wrapper.sh ${D}${bindir}/
    
    # Install systemd service
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/launcher.service ${D}${systemd_system_unitdir}/
    install -d ${D}${systemd_system_unitdir}/graphical.target.wants
    ln -s ../launcher.service ${D}${systemd_system_unitdir}/graphical.target.wants/launcher.service
    
    # Install desktop file
    install -d ${D}${datadir}/applications
    install -m 0644 ${WORKDIR}/launcher.desktop ${D}${datadir}/applications/
}

FILES:${PN} = "${bindir}/* ${systemd_system_unitdir}/* ${systemd_system_unitdir}/graphical.target.wants/* ${datadir}/applications/launcher.desktop"