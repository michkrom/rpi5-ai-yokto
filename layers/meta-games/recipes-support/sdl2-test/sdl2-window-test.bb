SUMMARY = "SDL2 window initialization test"
DESCRIPTION = "Test SDL2 window creation with OpenGL ES 2.0 (chocolate-doom style)"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://sdl2-window-test.c"

DEPENDS = "libsdl2 virtual/libgles2"

do_compile() {
    ${CC} ${CFLAGS} ${WORKDIR}/sdl2-window-test.c -o ${B}/sdl2-window-test ${LDFLAGS} -lSDL2 -lGLESv2 -DGL_GLEXT_PROTOTYPES
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/sdl2-window-test ${D}${bindir}/
}