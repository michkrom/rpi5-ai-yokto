# Yocto recipe for the AI scripts: menu (model downloader / llama-server
# control / chat launcher), langchain-chat client and llama-chat CLI.

SUMMARY = "AI scripts - model download, llama-server control and chat launchers"
DESCRIPTION = "RAM-aware TUI + CLI to download GGUF models, run llama-server and launch langchain / llama-cli chats"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://ai-menu \
           file://langchain-chat \
           file://llama-chat \
           file://utils.py \
           file://ai-menu.service \
           file://ai-menu.desktop \
"

S = "${WORKDIR}"

RDEPENDS:${PN} = " \
    python3-core \
    python3-json \
    python3-io \
    python3 \
    wget \
    bash \
    llama-cpp \
    llama-server \
    whisper-cpp \
    python3-langchain \
"

RRECOMMENDS:${PN} += "alsa-utils"

inherit systemd

do_install() {
    # CLI tools
    install -d ${D}${bindir}
    install -m 0755 ${WORKDIR}/ai-menu ${D}${bindir}/ai-menu
    install -m 0755 ${WORKDIR}/langchain-chat ${D}${bindir}/langchain-chat
    install -m 0755 ${WORKDIR}/llama-chat ${D}${bindir}/llama-chat
    install -m 0644 ${WORKDIR}/utils.py ${D}${bindir}/utils.py

    # Model store must be writable by BOTH the on-screen TUI (runs as the
    # 'weston' user inside weston-terminal) and root (SSH / systemd llama-server).
    # This recipe owns the model download, so create it here world-writable
    # (sticky bit) so either context can add GGUF models.
    install -d -m 1777 ${D}/usr/share/models

    # systemd service - auto-start on the graphical session like the games
    # launcher. ai-menu handles model download on demand (no model on 1st boot).
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/ai-menu.service ${D}${systemd_system_unitdir}/
    install -d ${D}${systemd_system_unitdir}/graphical.target.wants
    ln -s ../ai-menu.service ${D}${systemd_system_unitdir}/graphical.target.wants/ai-menu.service

    # desktop entry (for the GUI session / manual launch)
    install -d ${D}${datadir}/applications
    install -m 0644 ${WORKDIR}/ai-menu.desktop ${D}${datadir}/applications/
}

FILES:${PN} = " \
    ${bindir}/ai-menu \
    ${bindir}/langchain-chat \
    ${bindir}/llama-chat \
    ${bindir}/utils.py \
    ${systemd_system_unitdir}/ai-menu.service \
    ${systemd_system_unitdir}/graphical.target.wants/ai-menu.service \
    ${datadir}/applications/ai-menu.desktop \
    usr/share/models \
"