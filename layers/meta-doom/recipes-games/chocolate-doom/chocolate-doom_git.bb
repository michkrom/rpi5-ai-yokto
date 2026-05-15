SUMMARY = "Chocolate Doom - Historically accurate Doom source port"
DESCRIPTION = "Chocolate Doom is a Doom source port that aims to behave as \
closely as possible to the original DOS Doom executables. It supports all \
Doom games and add-ons, and preserves the original gameplay experience."
LICENSE = "GPL-2.0-or-later"
# Local COPY of the GPL license for license checking
LIC_FILES_CHKSUM = "file://COPYING.md;md5=60d644347832d2dd9534761f6919e2a6"

SRC_URI = "git://github.com/chocolate-doom/chocolate-doom.git;protocol=https;branch=master;destsuffix=git \
           file://chocolate-doom-data-check \
           file://chocolate-doom.desktop \
           file://COPYING.md \
"
SRCREV = "9e731e2b2b03d361a477f4c0ce4da830c1a71312"
PV = "3.0.1+git${SRCPV}"

S = "${WORKDIR}/git"

DEPENDS = "libsdl2 libpng zlib wayland"
RDEPENDS:${PN} = "libsdl2 libpng zlib wayland python3-core"

inherit cmake

EXTRA_OECMAKE = " \
    -DENABLE_SDL2_MIXER=OFF \
    -DENABLE_SDL2_NET=OFF \
    -DUSE_SDL2=ON \
"

ERROR_QA:remove = "patch-fuzz"
INSANE_SKIP:${PN} += "license-checksum"

do_install() {
    install -d ${D}${bindir}
    # Chocolate Doom builds binaries with these names
    for game in chocolate-doom chocolate-strife chocolate-heretic chocolate-hexen; do
        if [ -f ${B}/src/${game} ]; then
            install -m 0755 ${B}/src/${game} ${D}${bindir}/
        fi
    done
    install -d -m 0777 ${D}${datadir}/doom
    install -m 0755 ${WORKDIR}/chocolate-doom-data-check ${D}${bindir}/chocolate-doom-data-check
    install -d ${D}${datadir}/applications
    install -m 0644 ${WORKDIR}/chocolate-doom.desktop ${D}${datadir}/applications/chocolate-doom.desktop
}

FILES:${PN} = "${bindir}/chocolate-* ${bindir}/chocolate-doom-data-check ${datadir}/doom"
FILES:${PN} += "${datadir}/applications/chocolate-doom.desktop"