SUMMARY = "Systemd service for LLaMA server"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://llama-server.service"

RDEPENDS:${PN} = "llama-cpp"

inherit systemd

do_install() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/llama-server.service ${D}${systemd_system_unitdir}/
    # Do NOT auto-enable: the model at /usr/share/models/llama-model.gguf is
    # only present after the user downloads one (ai-menu). Start it on demand
    # with 'ai-menu --server start' or 'systemctl start llama-server'.
}

FILES:${PN} = "${systemd_system_unitdir}/llama-server.service"