SUMMARY = "Yokto Game Launcher - Simple TUI for game selection"
DESCRIPTION = "A lightweight text-based UI to launch games and download game data"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://game-launcher \
           file://game-launcher.desktop \
           file://game-launcher-autostart.sh \
"

S = "${WORKDIR}"

RDEPENDS:${PN} = "python3-core"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${WORKDIR}/game-launcher ${D}${bindir}/
    install -d ${D}${datadir}/applications
    install -m 0644 ${WORKDIR}/game-launcher.desktop ${D}${datadir}/applications/
    install -d ${D}${sysconfdir}/xdg/weston/startup
    install -m 0755 ${WORKDIR}/game-launcher-autostart.sh ${D}${sysconfdir}/xdg/weston/startup/game-launcher.sh
}

FILES:${PN} = "${bindir}/game-launcher ${datadir}/applications/game-launcher.desktop"
FILES:${PN} += "${sysconfdir}/xdg/weston/startup/game-launcher.sh"