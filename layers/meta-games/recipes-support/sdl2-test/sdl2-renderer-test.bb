SUMMARY = "SDL2 renderer test (chocolate-doom style)"
DESCRIPTION = "Test SDL2 window and renderer creation - mimics how chocolate-doom works"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://sdl2-renderer-test.c"

DEPENDS = "libsdl2"

do_compile() {
    ${CC} ${CFLAGS} ${WORKDIR}/sdl2-renderer-test.c -o ${B}/sdl2-renderer-test ${LDFLAGS} -lSDL2
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/sdl2-renderer-test ${D}${bindir}/
}