FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

ARG USER_ID=1000
ARG GROUP_ID=1000

# Single consolidated layer for all packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core build tools
    build-essential \
    chrpath \
    cpio \
    curl \
    diffstat \
    file \
    gawk \
    gcc-multilib \
    git \
    iputils-ping \
    locales \
    lz4 \
    socat \
    sudo \
    texinfo \
    unzip \
    util-linux \
    wget \
    xz-utils \
    zstd \
    # Python + Yocto deps
    python3 \
    python3-pip \
    python3-setuptools \
    python3-jinja2 \
    python3-git \
    python3-pexpect \
    python3-yaml \
    python3-voluptuous \
    # GUI/graphics (optional for QEMU/Wayland)
    libegl1 \
    libgl1-mesa-dev \
    libsdl1.2-dev \
    xterm \
    # Dev quality of life
    pylint \
    tmux \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Generate locale
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen en_US.UTF-8

ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
RUN pip3 install --no-cache-dir --break-system-packages kas
RUN apt-get update && apt-get install -y --no-install-recommends udev \
    && rm -rf /var/lib/apt/lists/*

# Create user with matching host UID/GID
RUN groupmod -n yocto ubuntu && groupmod -g ${GROUP_ID} yocto && \
    usermod -l yocto -m -d /home/yocto -u ${USER_ID} ubuntu && \
    echo "yocto:yocto" | chpasswd && \
    usermod -aG sudo yocto && \
    chown -R yocto:yocto /home/yocto

USER yocto
WORKDIR /home/yocto

CMD ["/bin/bash"]
