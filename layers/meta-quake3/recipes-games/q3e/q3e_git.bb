SUMMARY = "Quake3e - Modern Quake III Arena engine with Vulkan support"
DESCRIPTION = "A modern Quake III Arena engine aimed to be fast, secure and compatible \
with all existing Q3A mods. Features optimized OpenGL and Vulkan renderers."
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://COPYING.txt;md5=87113aa2b484c59a17085b5c3f900ebf"

SRC_URI = "git://github.com/ec-/Quake3e.git;protocol=https;branch=main;destsuffix=git \
           file://0001-Guard-glx.h-include-with-USE_OPENGL_API.patch \
           file://q3e-data-check \
           file://q3e.desktop \
"
SRCREV = "ed1064f80fda9cde2e7d33c2d5dce8f8166b12bd"
PV = "1.0+git${SRCPV}"

S = "${WORKDIR}/git"

DEPENDS = "libsdl2 curl vulkan-loader"
RDEPENDS:${PN} = "libsdl2 curl vulkan-loader python3-core"

inherit cmake

ERROR_QA:remove = "patch-fuzz"

INSANE_SKIP:${PN} += "license-checksum"

EXTRA_OECMAKE = " \
    -DUSE_SDL=ON \
    -DUSE_VULKAN=ON \
    -DUSE_OPENGL=OFF \
    -DUSE_CURL=ON \
    -DUSE_RENDERER_DLOPEN=OFF \
    -DRENDERER_DEFAULT=vulkan \
"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/quake3e.${TARGET_ARCH} ${D}${bindir}/quake3e
    install -m 0755 ${B}/quake3e.ded.${TARGET_ARCH} ${D}${bindir}/quake3e.ded
    install -d -m 0777 ${D}${datadir}/q3e/baseq3
    ln -s ${datadir}/q3e/baseq3 ${D}${bindir}/baseq3
    install -m 0755 ${WORKDIR}/q3e-data-check ${D}${bindir}/q3e-data-check
    install -d ${D}${datadir}/applications
    install -m 0644 ${WORKDIR}/q3e.desktop ${D}${datadir}/applications/q3e.desktop
}

FILES:${PN} = "${bindir}/quake3e ${bindir}/quake3e.ded ${bindir}/q3e-data-check ${bindir}/baseq3"
FILES:${PN} += "${datadir}/q3e/baseq3"
FILES:${PN} += "${datadir}/applications/q3e.desktop"