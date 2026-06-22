# rpi5-ai-yokto: Raspberry Pi 5 Yocto Build with AI-Supported Build Process

Kas-based Yocto build system targeting Raspberry Pi 5 (scarthgap / 5.0.17) with AI-assisted build processes for Kas/Yocto operations, fully dockerized for consistent builds. Contains multiple image levels with increasing functionality from headless to graphical applications.

This project includes AI agent tools built with [PI](https://github.com/badlogic/pi) and [OpenCode](https://opencode.net), enabling intelligent automation and troubleshooting of the build process. The build system exposes functionality through MCP (Model Context Protocol) tools that can be discovered and used by AI agents. See [AGENTS.md](AGENTS.md) for detailed guidance on using these tools.

## Prerequisites

- Docker, docker-build
- [Invoke](https://www.pyinvoke.org/) (`pip install invoke`)

## Image Levels

| Level | Description |
|-------|-------------|
| **base** | Minimal headless image |
| **wayland** | base + Wayland desktop + Weston compositor |
| **games**  | wayland + Quake3e + Chocolate Doom (gaming engines) |
| **chrome** | games + Chromium browser |
| **ai** | wayland + llama-cpp + whisper-cpp + llama-server (AI inference tools) |

Each level builds upon the previous one in the chain: **base → wayland → games → chrome → ai**. The base level provides a minimal system, wayland adds a graphical desktop environment, games adds gaming engines, chrome adds a web browser, and ai adds AI inference tools with a systemd service.

> **Warning:** The Chrome level build can take several hours to days. It requires building Chromium from source, which needs Rust, Clang, and the full Chromium codebase - a process requiring significant time and disk space (~100GB+). Games level is significantly faster as it only builds smaller game engines.

## Usage

```bash
# Quick shortcuts (in this directory)
./doksh <cmd>   # Run command in container, or interactive shell if no args
./doksh         # Start interactive shell in container

# Build container (one-time)
invoke docker-init
invoke docker-init --no-cache   # Force rebuild

# Checkout Yocto layers (no build)
invoke build-checkout --ai --detach        # For AI level (background)
invoke build-checkout --chrome --detach    # For Chrome level (background)
invoke build-checkout --wayland            # Wayland level (foreground)
invoke build-checkout --base --update      # Force update layers
invoke build-checkout --force              # Overwrite existing config

# Build image (detached mode recommended)
invoke build-start --ai --detach           # AI level (background)
invoke build-start --chrome --detach       # Chrome level (background)
invoke build-start --wayland               # Wayland level (foreground)
invoke build-start --base --detach         # Base level (background)
invoke build-start --games --detach        # Games level (background)

# Monitor detached builds
invoke build-status                        # Check running status
invoke build-last                          # Show recent log output
invoke build-stop                          # Stop running build

# Interactive shell with kas environment
invoke shell                               # Default (core level)
invoke shell --wayland                     # Wayland level environment
invoke shell --chrome --command "bitbake -c listtasks core-image-weston"

# Flash to SD card
invoke flash --device /dev/sdb --ai      # Flash AI image
invoke flash --device /dev/sdb --chrome    # Flash chrome image
invoke flash --device /dev/sdb --wayland   # Flash wayland image
invoke flash --device /dev/sdb --games     # Flash games image
invoke flash --device /dev/sdb --force     # Skip removable drive check

# List built images
invoke images

# Generate SWU update file from built image
invoke swu-generate --chrome --detach     # Generate .swu for chrome level
invoke swu-generate --wayland            # Generate .swu for wayland level

# Flash SWU to SD card (finds latest .swu for specified level)
invoke swu-flash --chrome --device /dev/sdb

# Apply SWU to running target device (finds latest .swu for specified level)
invoke swu-apply --chrome --host 192.168.1.100

# Container management
invoke container-status     # Check image/container status
invoke container-start      # Start background container
invoke container-stop       # Stop container
invoke container-shell      # Interactive shell (no kas setup)
invoke container-exec --command "ls -la"  # Run command in container

# Clean build artifacts
invoke build-clean                        # Remove build output (keeps downloads/sstate)
invoke build-clean --layers               # Also remove kas-cloned layers
invoke build-clean --sstate               # Also remove sstate cache
invoke build-clean --recipe=chromium      # Clean specific recipe from sstate
invoke build-clean --all                  # Remove everything

# Full rebuild (clean layers + build)
invoke build-rebuild --chrome             # Clean rebuild chrome level

# Remove Docker image and containers
invoke docker-purge
```

### Detached Build Output

When using `--detach`, build logs are saved to:
- `build-core.log`
- `build-wayland.log`
- `build-chrome.log`
- `build-games.log`

## Project Structure

```
yokto/
├── dockerfile
├── .dockerignore
├── tasks.py                # Invoke tasks
├── kas/
│   ├── core.yml            # Base config (RPi5 + scarthgap + shared)
│   ├── wayland.yml         # → core-image-weston + Wayland
│   ├── games.yml           # → core-image-games + Quake3e + Doom
│   └── chrome.yml          # → core-image-chrome + Chromium (includes games)
├── layers/                   # Gitignored wholesale. Kas clones layers here.
│   ├── poky/                   # OE-Core (cloned by kas)
│   ├── meta-raspberrypi/       # RPi BSP (cloned by kas)
│   ├── meta-games/             # Custom layer: Game recipes
│   └── meta-doom/              # Custom layer: Chocolate Doom recipe
├── build/                    # Build output (gitignored)
│   └── deploy/images/raspberrypi5/
└── .pi/
    └── extensions/
        ├── invoke/           # PI extension with invoke-based tools
        └── target/           # PI extension with SSH/SCP tools for target
```

## Layers

Kas clones layers into `layers/` (gitignored wholesale). To add custom layers,
place them in `layers/` and reference them in `kas/base.yml` under `repos`.

The `meta-base` layer contains:
- SWU update generation recipes (`recipes-core/swupdate/`)
- SDL2 Wayland-EGL patch for symbol visibility
- Mesa and Weston configuration tweaks for RPi5

The `meta-games` layer contains:
- Quake3e recipe (`recipes-games/q3e/`)
- Game launcher TUI (`recipes-core/launcher/`)

The `meta-doom` layer contains:
- Chocolate Doom recipe (`recipes-games/chocolate-doom/`)

## Configuration

### Machine + Distro
- `MACHINE = "raspberrypi5"`
- `DISTRO = "poky"`

### All levels
- `INIT_MANAGER = "systemd"`
- `IMAGE_FSTYPES = "wic.bz2"`
- `LICENSE_FLAGS_ACCEPTED = "synaptics-killswitch"`
- `IMAGE_NAME` set per level for distinct output files

### Wayland level adds
- `DISTRO_FEATURES:append = " wayland pam"`
- `DISTRO_FEATURES:remove = " x11"`
- `CORE_IMAGE_EXTRA_INSTALL += "weston-examples mesa-megadriver"`

### Games level adds
- `CORE_IMAGE_EXTRA_INSTALL += "q3e chocolate-doom game-launcher mesa-megadriver"` — Gaming engines and launcher

### Chrome level adds
- `IMAGE_INSTALL:append = " chromium-ozone-wayland"` — Chromium browser (includes all games)

### AI level adds
- `CORE_IMAGE_EXTRA_INSTALL += "llama-cpp whisper-cpp llama-server"` — AI inference tools (llama.cpp, whisper.cpp)
- Provides `image-ai` target with LLaMA server systemd service for local AI inference

## meta-games and meta-doom Layers (Custom)

The `layers/meta-games/` layer contains:

**Game Launcher** (`recipes-core/game-launcher/`):
- Simple text-based UI for game selection and data download
- Autostarts on Weston desktop login
- Offers to download Quake 3 demo data or Freedoom (free Doom assets)

**Quake3e** (`recipes-games/q3e/`):
- Modern Quake III Arena engine with Vulkan support
- Recipe: `q3e_git.bb` — builds from `github.com/ec-/Quake3e.git`
- Build deps: `libsdl2`, `curl`, `vulkan-loader`
- Installs `quake3e`, `quake3e.ded`, and `q3e-data-check` utility

The `layers/meta-doom/` layer contains:

**Chocolate Doom** (`recipes-games/chocolate-doom/`):
- Historically accurate Doom source port
- Recipe: `chocolate-doom_git.bb`
- Supports Doom, Doom 2, Heretic, and Hexen
- Build deps: `libsdl2`, `sdl-mixer`, `libpng`, `zlib`
- Ready for Freedoom WAD files (downloadable via launcher)

The `layers/meta-ai/` layer contains:

**LLaMA.cpp** (`recipes-ai/llama-cpp/llama-cpp_git.bb`):
- LLaMA inference library in C/C++
- Provides `llama-cli` and `llama-server` binaries
- Builds shared libraries: `libggml*`, `libllama*`, `libmtmd*`

**Whisper.cpp** (`recipes-ai/whisper-cpp/whisper-cpp_git.bb`):
- Speech recognition library in C/C++
- Provides `whisper-cli` and `whisper-stream` binaries
- Builds `libwhisper*` shared library (depends on llama-cpp for libggml)

**LLaMA Server** (`recipes-core/llama-server/llama-server_1.0.bb`):
- Systemd service for LLaMA inference server
- Listens on port 8080 by default
- Can serve models from `/usr/share/models/`

## Build Output

```
build/deploy/images/raspberrypi5/
├── core-image-base-raspberrypi5.rootfs.wic.bz2    # base level
├── core-image-wayland-raspberrypi5.rootfs.wic.bz2  # wayland level
├── core-image-games-raspberrypi5.rootfs.wic.bz2    # games level
├── core-image-chrome-raspberrypi5.rootfs.wic.bz2   # chrome level (includes games)
├── image-ai-raspberrypi5.rootfs.wic.bz2           # ai level
├── image-ai.swu                                  # ai level OTA update
├── Image-*.bin                                    # Kernel
├── *.dtb / *.dtbo                                 # Device trees
└── bootfiles/                                     # RPi firmware
```

Your warranty. You have been warned.">
## SWU (OTA Update) Support

This project supports OTA (Over-The-Air) updates using SWUpdate. The system can generate `.swu` update files and apply them to running systems.

### Building with SWUpdate

SWUpdate is included in all image levels. To add it manually:

```bash
# SWUpdate is automatically included in builds via core.yml
invoke build-start --wayland --detach
```

### Generating Update Files (.swu)

After building an image, generate a `.swu` update file:

```bash
# Generate .swu from the most recent built image
invoke swu-generate --ai --detach         # Generate .swu for AI level
invoke swu-generate --chrome --detach     # Generate .swu for chrome level

# Check generated files
invoke images  # Shows both .wic.bz2 and .swu files
```

**SWU File Sizes:** The `.swu` files are typically ~270MB (similar to `.wic.bz2`) because images are stored compressed using gzip. The `compressed = "zlib"` flag in `sw-description` tells SWUpdate to decompress during installation.

The generated `.swu` file contains:
- The full disk image (extracted from `.wic.bz2`)
- A `sw-description` file with version hash and update instructions

### Applying Updates

**Option 1: Flash to SD card directly (offline update)**

```bash
# Extract and flash .swu to SD card
invoke flash-swu --swu yokto-chrome-*.swu --device /dev/sdb
```

**Option 2: Apply to running system (online update)**

```bash
# Copy and apply update to a running RPi5
scp yokto-chrome-*.swu root@192.168.1.100:/tmp/
scp yokto-ai-*.swu root@192.168.1.100:/tmp/
ssh root@192.168.1.100 "swupdate-apply.sh /tmp/yokto-chrome-*.swu"
ssh root@192.168.1.100 "swupdate-apply.sh /tmp/yokto-ai-*.swu"
# Then reboot to activate
```

### On-Target Update Process

The `swupdate-apply.sh` script on the target:
1. Stops the GUI (Weston) if running
2. Applies the update using `swupdate -i <file>`
3. Reports success (reboot required to activate)

### SWU File Structure

A `.swu` file is a cpio archive containing:
```
sw-description     # Update metadata (version, hash, image info)
image.wic.gz       # Gzipped disk image for RPi5 (compressed with zlib)
```

The `sw-description` format:
```
SOFTWARE_VERSION = "20241201-120000"
FILES_HASH = "sha256-hash-of-image"
ALLOW_DOWNGRADE = true
images: (
        {
                filename = "image.wic.gz"
                type = "raw"
                device = "/dev/mmcblk0"
                compressed = "zlib"
        }
)
```

The `compressed = "zlib"` directive tells SWUpdate to decompress the image before flashing.

## AI Agent Integration

This project includes AI agent capabilities through:

### MCP (Model Context Protocol) Tools

The build system exposes functionality through MCP tools that can be discovered by AI agents. These tools are thin wrappers around `invoke` tasks, ensuring a single source of truth.

**Container Tools:**
- `invoke_docker_init` — Build the yokto Docker container
- `invoke_container_status` — Check image/container status
- `invoke_container_start` — Start background container
- `invoke_container_stop` — Stop container
- `invoke_container_shell` — Interactive shell (no kas setup)
- `invoke_container_exec` — Run command in container
- `invoke_docker_purge` — Remove image and containers

**Build Tools:**
- `invoke_build_checkout` — Fetch/update layers (supports `--detach` for background)
- `invoke_build_start` — Build image (supports `--detach` for background builds)
- `invoke_build_stop` — Stop running build
- `invoke_build_status` — Check running status + tail logs
- `invoke_build_last` — Show recent build result
- `invoke_shell` — Run command in kas shell or open interactive shell
- `invoke_build_clean` — Remove build artifacts
- `invoke_build_rebuild` — Clean rebuild from scratch
- `invoke_images` — List built images
- `invoke_flash` — Flash image to SD card

**Target Device Tools (SSH to RPi5):**
- `target_connect` — Connect to RPi5 via SSH
- `target_disconnect` — Disconnect from target
- `target_status` — Show connection status
- `target_exec` — Run command via SSH
- `target_run_as_root` — Run command as root via SSH
- `target_copy` — Copy files via SCP

### PI Extensions

The `.pi/extensions/` directory contains PI extensions that auto-discover and register tools:

- **invoke extension** (`.pi/extensions/invoke/`): Wraps invoke tasks for container and build operations. Provides tools like `invoke_build_start`, `invoke_build_checkout`, etc.
- **target extension** (`.pi/extensions/target/`): Direct SSH/SCP tools for target device interaction. Provides tools like `target_connect`, `target_exec`, etc.

These extensions provide:
- Tool name matching invoke tasks with `invoke_` prefix
- Full parameter support with TypeScript types
- Prompt snippets and guidelines for `invoke_build_start` to guide AI agents
- Target device state management via environment variables
