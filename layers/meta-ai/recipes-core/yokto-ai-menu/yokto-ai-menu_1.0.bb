# Yocto recipe for the AI menu (model downloader / llama-server control / chat launcher)

SUMMARY = "Yokto AI Menu - model download, llama-server and chat launcher"
DESCRIPTION = "RAM-aware TUI + CLI to download GGUF models, run llama-server and launch langchain / llama-cli chats"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://ai-menu \
           file://langchain-chat \
           file://ai-menu.service \
           file://ai-menu.desktop \
"

S = "${WORKDIR}"

RDEPENDS:${PN} = " \
    python3-core \
    python3-json \
    python3-io \
    wget \
    bash \
    llama-cpp \
    llama-server \
    yokto-chat \
    python3-langchain \
"

inherit systemd

do_install() {
    # CLI tools
    install -d ${D}${bindir}
    install -m 0755 ${WORKDIR}/ai-menu ${D}${bindir}/ai-menu
    install -m 0755 ${WORKDIR}/langchain-chat ${D}${bindir}/langchain-chat

    # systemd service (installed but NOT enabled - models are downloaded on demand)
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/ai-menu.service ${D}${systemd_system_unitdir}/

    # desktop entry (optional for the GUI session)
    install -d ${D}${datadir}/applications
    install -m 0644 ${WORKDIR}/ai-menu.desktop ${D}${datadir}/applications/
}

FILES:${PN} = " \
    ${bindir}/ai-menu \
    ${bindir}/langchain-chat \
    ${systemd_system_unitdir}/ai-menu.service \
    ${datadir}/applications/ai-menu.desktop \
"