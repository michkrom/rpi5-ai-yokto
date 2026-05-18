# swupdate-apply script for applying updates on target

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://swupdate-apply.sh"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${WORKDIR}/swupdate-apply.sh ${D}${bindir}/swupdate-apply.sh
}