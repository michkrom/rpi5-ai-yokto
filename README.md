# rpi5-ai-yokto: Raspberry Pi 5 Yocto Build with AI-Supported Build Process

Kas-based Yocto build system targeting Raspberry Pi 5 (scarthgap / 5.0.17) with AI-assisted build processes for Kas/Yocto operations, fully dockerized for consistent builds. Contains multiple image levels with increasing functionality from headless to graphical applications.

This project includes AI agent tools built with [PI](https://github.com/badlogic/pi) and [OpenCode](https://opencode.net), enabling intelligent automation and troubleshooting of the build process. The build system exposes functionality through MCP (Model Context Protocol) tools that can be discovered and used by AI agents. See [AGENTS.md](AGENTS.md) for detailed guidance on using these tools.

## Prerequisites

- Docker, docker-build
- [Invoke](https://www.pyinvoke.org/) (`pip install invoke`)

## Image Levels

| Level | Description |
|-------|-------------|
| **core** | Minimal headless image |
| **wayland** | core + Wayland desktop + Weston compositor |
| **chrome**  | wayland + Chromium browser |
| **quake3**  | wayland + Quake3e (Vulkan Quake 3 engine) |

Each level builds upon the previous one, adding more functionality. The core level provides a minimal system, wayland adds a graphical desktop environment, chrome includes a web browser, and quake3 adds a gaming engine.

## Usage

```bash
# Build container (one-time)
invoke docker-init
invoke docker-init --no-cache   # Force rebuild

# Checkout + build
invoke build                    # core (default)
invoke build --wayland
invoke build --chrome
invoke build --quake3

# Checkout only (no build)
invoke checkout
invoke checkout --update --force

# Interactive shell (sources checked out)
invoke shell
invoke docker-shell             # Plain docker bash

# Flash to SD card
invoke flash --device /dev/sdb
invoke flash --device /dev/sdb --wayland
invoke flash --device /dev/sdb --quake3
invoke flash --device /dev/sdb --force   # Skip removable check

# List built images
invoke images

# Remove container + image
invoke docker-purge

# Remove build output + kas-cloned layers (preserves downloads/sstate)
invoke clean
invoke clean --all   # Also wipe downloads/ and sstate-cache/

# Clean + checkout + build (preserves downloads/sstate)
invoke rebuild
invoke rebuild --wayland
```

## Project Structure

```
yokto/
├── dockerfile
├── .dockerignore
├── tasks.py                # Invoke tasks
├── kas/
│   ├── base.yml            # RPi5 + scarthgap + shared config
│   ├── core.yml            # → core-image-base
│   ├── wayland.yml         # → core-image-weston + Wayland
│       ├── chrome.yml          # → core-image-weston + Chromium
    └── quake3.yml          # → core-image-weston + Quake3e
├── layers/                   # Gitignored wholesale. Kas clones layers here.
│   ├── poky/                   # OE-Core (cloned by kas)
│       ├── meta-raspberrypi/       # RPi BSP (cloned by kas)
    └── meta-quake3/            # Custom layer: Quake3e recipe
├── build/                  # Build output (gitignored)
    └── deploy/images/raspberrypi5/
```

## Layers

Kas clones layers into `layers/` (gitignored wholesale). To add custom layers,
place them in `layers/` and reference them in `kas/base.yml` under `repos`.

The `meta-quake3` layer serves as a practical example of how to create and integrate your own custom layers.

## Configuration

### Machine + Distro
- `MACHINE = "raspberrypi5"`
- `DISTRO = "poky"`

### All levels
- `INIT_MANAGER = "systemd"`
- `IMAGE_FSTYPES = "wic.bz2"`
- `LICENSE_FLAGS_ACCEPTED = "synaptics-killswitch"`

### Wayland level adds
- `DISTRO_FEATURES:append = " wayland pam"`
- `DISTRO_FEATURES:remove = " x11"`
- `CORE_IMAGE_EXTRA_INSTALL += "weston-init"`

### Chrome level adds
- `CORE_IMAGE_EXTRA_INSTALL += "chromium-ozone-wayland"`

### Quake3 level adds
- `CORE_IMAGE_EXTRA_INSTALL += "q3e"` — Quake3e engine (Vulkan renderer)

## meta-quake3 Layer (Custom)

The `layers/meta-quake3/` layer contains a recipe for **Quake3e** — a modern Quake III Arena engine with Vulkan support.

- Recipe: `recipes-games/q3e/q3e_git.bb` — builds from `github.com/ec-/Quake3e.git` with `USE_VULKAN=ON`, `USE_OPENGL=OFF`
- Build deps: `libsdl2`, `curl`, `vulkan-loader`
- Installs `quake3e` (engine), `quake3e.ded` (dedicated server), and a `q3e-data-check` Python utility
- Integrates with Weston via autostart script at `/etc/xdg/weston/startup/q3e-data-check.sh` — checks for game data (`pak*.pk3` files) on boot
- Game data directory: `/usr/share/q3e/baseq3/` (world-writable)
- Includes a `.desktop` file for launching from the Weston desktop

## Build Output

```
build/deploy/images/raspberrypi5/
├── core-image-base-raspberrypi5.rootfs.wic.bz2    # core level
├── core-image-weston-raspberrypi5.rootfs.wic.bz2  # wayland/chrome
├── Image-*.bin                                    # Kernel
├── *.dtb / *.dtbo                                 # Device trees
└── bootfiles/                                     # RPi firmware
```

## AI Agent Integration

This project includes AI agent capabilities through:

- **MCP Server Tools**: Exposes build system functionality through standardized Model Context Protocol tools
- **PI Extension**: Custom tools for Yocto operations that can be discovered by AI agents
- **Agent Guidance**: See [AGENTS.md](AGENTS.md) for detailed information on using AI-assisted build processes

The agent can automatically discover tools like `yocto_build_start`, `yocto_build_logs`, and others to intelligently automate and troubleshoot the build process.
