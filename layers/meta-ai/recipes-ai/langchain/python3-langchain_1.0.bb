# Bake langchain (and friends) into the OS rootfs at build time.
#
# Why pip here: langchain's dependency tree (pydantic-core, jiter, tiktoken,
# openai, ...) is not packaged in OpenEmbedded, and the closed yokto image must
# NOT need pip on the target. So at *build* time we use the native pip from
# python3-pip-native to pull aarch64 manylinux wheels straight into the target
# site-packages. The image then just ships the baked packages.
#
#   - aarch64 wheels are fetched with --platform manylinux_2_28_aarch64
#     (glibc in scarthgap is newer, so 2_17/2_28 wheels are all compatible)
#   - --only-binary=:all: guarantees we never build from source on the host
#   - network access is required at build time (same as layer/model downloads)

SUMMARY = "langchain + langchain-openai Python packages baked into the AI image"
HOMEPAGE = "https://github.com/langchain-ai/langchain"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

inherit python3-dir python3native

# Native pip that runs on the build host during do_install
DEPENDS += "python3-pip-native"

RDEPENDS:${PN} += " \
    python3-core \
    python3-json \
    python3-io \
    python3-compile \
"

# Versions validated locally (see langchain-chat testing); keep aligned with
# the chat script's expectations. Note: pip pulls the full transitive tree
# (pydantic, pydantic-core, openai, jiter, httpx, langsmith, tenacity, ...).
LANGCHAIN_VERSION ?= "==1.3.15"
LANGCHAIN_OPENAI_VERSION ?= "==1.5.1"
# Official HuggingFace python API used by ai-menu for model downloads
HF_HUB_VERSION ?= "==1.6.0"

do_install() {
    # Target site-packages must exist before --target install
    install -d ${D}${PYTHON_SITEPACKAGES_DIR}

    export PIP_DISABLE_PIP_VERSION_CHECK=1
    export PIP_NO_CACHE_DIR=1
    export PYTHONNOUSERSITE=1

    # --target + explicit platform -> fetch aarch64 manylinux wheels only.
    # pip refuses to build anything; pure-python wheels install as-is.
    ${PYTHON} -m pip install \
        --platform manylinux_2_28_aarch64 \
        --python-version ${PYTHON_BASEVERSION} \
        --only-binary=:all: \
        --target ${D}${PYTHON_SITEPACKAGES_DIR} \
        "langchain${LANGCHAIN_VERSION}" \
        "langchain-openai${LANGCHAIN_OPENAI_VERSION}" \
        "huggingface-hub${HF_HUB_VERSION}" \
        2>&1 | tee ${WORKDIR}/pip-install.log

    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        bbfatal "pip install of langchain failed - see ${WORKDIR}/pip-install.log"
    fi

    # Wheels ship .pyc-free .so files; strip stray bytecode for cleanliness
    find ${D}${PYTHON_SITEPACKAGES_DIR} -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
}

# Pip-baked wheels: .so are pre-stripped, deps are pull-time (not package
# manager) resolvable, and RECORD files may contain build-time paths.
INSANE_SKIP:${PN} += "already-stripped file-rdeps buildpaths"

FILES:${PN} = "${PYTHON_SITEPACKAGES_DIR}/*"