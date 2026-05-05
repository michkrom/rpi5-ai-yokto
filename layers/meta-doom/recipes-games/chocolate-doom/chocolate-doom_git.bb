SUMMARY = "Chocolate Doom - Historically accurate Doom source port"
DESCRIPTION = "Chocolate Doom is a Doom source port that aims to behave as \
closely as possible to the original DOS Doom executables. It supports all \
Doom games and add-ons, and preserves the original gameplay experience."
LICENSE = "GPL-2.0-or-later"
LIC_FILES_CHKSUM = "file://COPYING;md5=87113aa2b484c59a17085b5c3f900ebf"

SRC_URI = "git://github.com/chocolate-doom/chocolate-doom.git;protocol=https;branch=master \
           file://chocolate-doom-data-check \
           file://chocolate-doom.desktop \
"
SRCREV = "${AUTOREV}"
PV = "3.0.1+git${SRCPV}"

S = "${WORKDIR}/git"

DEPENDS = "libsdl2 sdl-mixer libpng zlib"
RDEPENDS:${PN} = "libsdl2 sdl-mixer libpng zlib python3-core"

inherit autotools

EXTRA_OECONF = " \
    --disable-homedir-config \
"

do_install() {
    install -d ${D}${bindir}
    # Chocolate Doom builds binaries in src/ with specific names
    for game in doom strife heretic hexen; do
        if [ -f ${B}/src/chocolate-${game} ]; then
            install -m 0755 ${B}/src/chocolate-${game} ${D}${bindir}/
        fi
    done
    install -d -m 0777 ${D}${datadir}/doom
    install -m 0755 ${WORKDIR}/chocolate-doom-data-check ${D}${bindir}/chocolate-doom-data-check
    install -d ${D}${datadir}/applications
    install -m 0644 ${WORKDIR}/chocolate-doom.desktop ${D}${datadir}/applications/chocolate-doom.desktop
}

FILES:${PN} = "${bindir}/chocolate-* ${bindir}/chocolate-doom-data-check ${datadir}/doom"
FILES:${PN} += "${datadir}/applications/chocolate-doom.desktop"