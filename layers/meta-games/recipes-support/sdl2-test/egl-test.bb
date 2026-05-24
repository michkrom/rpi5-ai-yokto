SUMMARY = "EGL Wayland visual test"
DESCRIPTION = "A simple EGL test that creates a colorful animated display"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://egl-test.c"

DEPENDS = "virtual/egl wayland virtual/libgles2"

do_compile() {
    ${CC} ${CFLAGS} ${WORKDIR}/egl-test.c -o ${B}/egl-test ${LDFLAGS} -lEGL -lwayland-egl -lwayland-client -lGLESv2 -lm
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/egl-test ${D}${bindir}/
}