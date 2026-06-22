SUMMARY = "LLaMA inference in C/C++ (llama.cpp)"
HOMEPAGE = "https://github.com/ggerganov/llama.cpp"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=223b26b3c1143120c87e2b13111d3e99"

SRC_URI = "git://github.com/ggerganov/llama.cpp.git;protocol=https;branch=master"
SRCREV = "${AUTOREV}"
PV = "1.0+git${SRCPV}"

S = "${WORKDIR}/git"

DEPENDS = "cmake-native ninja-native libsdl2 alsa-lib wayland libdrm virtual/libgles2"

inherit cmake

# Explicit compiler flags targeting Raspberry Pi 5's Cortex-A76 (ARMv8.2-A)
# Using :rpi override targets all Raspberry Pi boards via meta-raspberrypi SOC family
TARGET_CFLAGS:append:rpi = " -mcpu=cortex-a76 "
TARGET_CXXFLAGS:append:rpi = " -mcpu=cortex-a76 "

# Build CLI tools without tests or unstable backends
EXTRA_OECMAKE = " \
    -DLLAMA_BUILD_TESTS=OFF \
    -DLLAMA_BUILD_EXAMPLES=ON \
    -DLLAMA_BUILD_SERVER=ON \
    -DLLAMA_VULKAN=OFF \
    -DLLAMA_CUDA=OFF \
    -DLLAMA_HIPBLAS=OFF \
    -DLLAMA_METAL=OFF \
"

# Install CLI and server binaries and shared libraries
do_install() {
    install -d ${D}${bindir}
    for bin in llama-cli llama-server; do
        if [ -f "${B}/bin/${bin}" ]; then
            install -m 0755 "${B}/bin/${bin}" ${D}${bindir}/
        fi
    done
    # Install shared libraries
    install -d ${D}${libdir}
    install -m 0755 ${B}/bin/lib*.so* ${D}${libdir}/ 2>/dev/null || true
}

FILES:${PN} += "${bindir}/llama-cli ${bindir}/llama-server ${libdir}"

# Keep all libraries in main package (don't split to -dev)
FILES:${PN}-dev = ""

# Allow patch fuzz and skip QA checks for bundled libraries
ERROR_QA:remove = "patch-fuzz"
INSANE_SKIP:${PN} += "dev-elf file-rdeps"

# Runtime dependency for model management
RDEPENDS:${PN} += "bash"