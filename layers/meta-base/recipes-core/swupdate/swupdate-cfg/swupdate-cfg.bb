SUMMARY = "SWUpdate configuration file for Yokto images"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
inherit allarch

SRC_URI = "file://swupdate.cfg"

S = "${WORKDIR}"

do_install() {
    install -d ${D}${sysconfdir}
    install -m 0644 ${S}/swupdate.cfg ${D}${sysconfdir}/swupdate.cfg
    echo "Package swupdate-cfg installed at \
${D}${sysconfdir}/swupdate.cfg"
}

FILES:${PN} += "${sysconfdir}/swupdate.cfg"