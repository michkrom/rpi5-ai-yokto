# Yocto recipe for yokto-chat Python application

SUMMARY = "Yokto Chat - Text and voice interface for AI tools"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/files/common-licenses/MIT;md5=0835ade698e0bcf8506ecda69fda7663"

SRC_URI = "file://yokto-chat"

RDEPENDS:${PN} += "python3 llama-cpp whisper-cpp"
RRECOMMENDS:${PN} += "alsa-utils"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${WORKDIR}/yokto-chat ${D}${bindir}/yokto-chat
}

FILES:${PN} = "${bindir}/yokto-chat"