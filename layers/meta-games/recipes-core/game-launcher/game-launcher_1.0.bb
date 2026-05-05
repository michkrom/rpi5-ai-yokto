SUMMARY = "Yokto Game Launcher - Simple TUI for game selection"
DESCRIPTION = "A lightweight text-based UI to launch games and download game data"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://COPYING;md5=87113aa2b484c59a17085b5c3f900ebf"

SRC_URI = "file://game-launcher \
           file://game-launcher.desktop \
           file://game-launcher-autostart.sh \
           file://COPYING \
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