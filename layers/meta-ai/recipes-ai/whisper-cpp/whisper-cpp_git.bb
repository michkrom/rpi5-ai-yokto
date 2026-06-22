SUMMARY = "Whisper speech recognition in C/C++"
HOMEPAGE = "https://github.com/ggml-org/whisper.cpp"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=223b26b3c1143120c87e2b13111d3e99"

SRC_URI = "git://github.com/ggml-org/whisper.cpp.git;protocol=https;branch=master"
SRCREV = "${AUTOREV}"
PV = "1.0+git${SRCPV}"

S = "${WORKDIR}/git"

DEPENDS = "cmake-native ninja-native libsdl2 alsa-lib wayland libdrm virtual/libgles2"

# Runtime dependency for libggml libraries from llama-cpp
RDEPENDS:${PN} = "llama-cpp"

inherit cmake

# Explicit compiler flags targeting Raspberry Pi 5's Cortex-A76 (ARMv8.2-A)
# Using :rpi override targets all Raspberry Pi boards via meta-raspberrypi SOC family
TARGET_CFLAGS:append:rpi = " -mcpu=cortex-a76 "
TARGET_CXXFLAGS:append:rpi = " -mcpu=cortex-a76 "

# Build examples with SDL2 support for real-time audio
EXTRA_OECMAKE = " \
    -DWHISPER_BUILD_TESTS=OFF \
    -DWHISPER_BUILD_EXAMPLES=ON \
    -DWHISPER_SDL2=ON \
"

do_install() {
    install -d ${D}${bindir}
    for bin in whisper-cli whisper-stream; do
        if [ -f "${B}/bin/${bin}" ]; then
            install -m 0755 "${B}/bin/${bin}" ${D}${bindir}/
        fi
    done
    # Install only whisper-specific libraries (libwhisper*), not libggml* (those come from llama-cpp)
    install -d ${D}${libdir}
    for f in ${B}/bin/libwhisper.so*; do
        if [ -f "$f" ]; then
            install -m 0755 "$f" ${D}${libdir}/
        fi
    done
}

# Install CLI tools and whisper library only (libggml from llama-cpp)
FILES:${PN} = "${bindir}/whisper-cli ${bindir}/whisper-stream ${libdir}"
FILES:${PN}-dev = ""

# Skip QA checks: dev-elf (libwhisper.so not a symlink), file-rdeps (libggml from llama-cpp)
INSANE_SKIP:${PN} += "dev-elf file-rdeps"