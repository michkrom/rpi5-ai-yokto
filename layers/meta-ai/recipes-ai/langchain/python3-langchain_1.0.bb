# Bake langchain (and friends) into the OS rootfs at build time.
#
# Why pip here: langchain's dependency tree (pydantic-core, jiter, tiktoken,
# openai, ...) is not packaged in OpenEmbedded, and the closed yokto image must
# NOT need pip on the target. So at *build* time we use the native pip from
# python3-pip-native to pull aarch64 manylinux wheels straight into the target
# site-packages. The image then just ships the baked packages.
#
#   - aarch64 wheels are fetched with --platform manylinux2014_aarch64
#     because pip does EXACT-prefix matching on a manual --platform, and
#     these wheels carry the manylinux2014_aarch64/2_17_aarch64 tags
#   - --only-binary=:all: guarantees we never build from source on the host
#   - hf-hub is pinned < 0.29 so the Rust hf-xet package (no aarch64 wheel)
#     is optional and not pulled in
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

# Versions validated locally (see langchain-chat / cross-bake testing); keep
# aligned with the chat script's expectations. pip pulls the full transitive
# tree (pydantic, pydantic-core, openai, jiter, httpx, langsmith, tenacity, ...).
LANGCHAIN_VERSION ?= "==1.3.15"
LANGCHAIN_OPENAI_VERSION ?= "==1.5.1"
# Official HuggingFace python API used by ai-menu for model downloads.
# Pin <0.29: 1.x/0.32+ hard-require the Rust hf-xet package which has no
# working aarch64 wheel, so older hub is used.
HF_HUB_VERSION ?= "==0.28.1"

do_install() {
    # Target site-packages must exist before --target install
    install -d ${D}${PYTHON_SITEPACKAGES_DIR}

    export PIP_DISABLE_PIP_VERSION_CHECK=1
    export PIP_NO_CACHE_DIR=1
    export PYTHONNOUSERSITE=1

    # --target + explicit platform -> fetch aarch64 manylinux wheels only.
    # pip refuses to build anything; pure-python wheels install as-is.
    ${PYTHON} -m pip install \
        --platform manylinux2014_aarch64 \
        --python-version ${PYTHON_BASEVERSION} \
        --only-binary=:all: \
        --target ${D}${PYTHON_SITEPACKAGES_DIR} \
        "langchain${LANGCHAIN_VERSION}" \
        "langchain-openai${LANGCHAIN_OPENAI_VERSION}" \
        "huggingface-hub${HF_HUB_VERSION}" \
        > ${WORKDIR}/pip-install.log 2>&1
    rc=$?
    echo "--- pip tail ---"
    tail -40 ${WORKDIR}/pip-install.log
    if [ $rc -ne 0 ]; then
        bbfatal "pip install of langchain failed (rc=$rc) - see ${WORKDIR}/pip-install.log"
    fi

    # Wheels ship .pyc-free .so files; strip stray bytecode for cleanliness
    find ${D}${PYTHON_SITEPACKAGES_DIR} -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
}

# Pip-baked wheels: .so are pre-stripped, deps are pull-time (not package
# manager) resolvable, and RECORD files may contain build-time paths.
# Pip-baked wheels are prebuilt without OE LDFLAGS (e.g. the Rust uuid_utils
# extension has no GNU_HASH) and may carry text relocations; skip those checks.
INSANE_SKIP:${PN} += "already-stripped file-rdeps buildpaths ldflags textrel"

FILES:${PN} = "${PYTHON_SITEPACKAGES_DIR}/*"