SUMMARY = "Systemd service for LLaMA server"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://llama-server.service"

RDEPENDS:${PN} = "llama-cpp"

inherit systemd

do_install() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/llama-server.service ${D}${systemd_system_unitdir}/
    
    # Enable the service by default
    install -d ${D}${systemd_system_unitdir}/multi-user.target.wants
    ln -s ../llama-server.service ${D}${systemd_system_unitdir}/multi-user.target.wants/llama-server.service
}

FILES:${PN} = "${systemd_system_unitdir}/llama-server.service ${systemd_system_unitdir}/multi-user.target.wants/llama-server.service"