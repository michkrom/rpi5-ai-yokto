SUMMARY = "Simple SDL2 EGL test program"
DESCRIPTION = "A minimal program to test SDL2 EGL initialization and rendering"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://sdl2-egl-test.c"

DEPENDS = "libsdl2 virtual/libgles2 wayland"
RDEPENDS:${PN} = "libsdl2 wayland"

do_compile() {
    ${CC} ${CFLAGS} ${WORKDIR}/sdl2-egl-test.c -o ${B}/sdl2-egl-test ${LDFLAGS} -lSDL2 -lGLESv2 -lm
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/sdl2-egl-test ${D}${bindir}/
}