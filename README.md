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
| **games**  | wayland + Quake3e + Chocolate Doom (gaming engines) |

Each level builds upon the previous one, adding more functionality. The core level provides a minimal system, wayland adds a graphical desktop environment, chrome includes a web browser, and games adds multiple gaming engines.

> **Warning:** The Chrome level build can take several hours to days. It requires building Chromium from source, which needs Rust, Clang, and the full Chromium codebase - a process requiring significant time and disk space (~100GB+).

## Usage

```bash
# Quick shortcuts (in this directory)
./doksh <cmd>   # Run command in container, or interactive shell if no args
./doksh         # Start interactive shell in container

# Build container (one-time)
invoke docker-init
invoke docker-init --no-cache   # Force rebuild

# Checkout Yocto layers (no build)
invoke build-checkout --chrome --detach    # For Chrome level (background)
invoke build-checkout --wayland            # Wayland level (foreground)
invoke build-checkout --core --update      # Force update layers
invoke build-checkout --force            # Overwrite existing config

# Build image (detached mode recommended)
invoke build-start --chrome --detach       # Chrome level (background)
invoke build-start --wayland               # Wayland level (foreground)
invoke build-start --core --detach         # Core level (background)
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
invoke flash --device /dev/sdb --chrome    # Flash chrome image
invoke flash --device /dev/sdb --wayland   # Flash wayland image
invoke flash --device /dev/sdb --games     # Flash games image
invoke flash --device /dev/sdb --force     # Skip removable drive check

# List built images
invoke images

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
│   ├── base.yml            # RPi5 + scarthgap + shared config
│   ├── core.yml            # → core-image-base
│   ├── wayland.yml         # → core-image-weston + Wayland
│   ├── chrome.yml          # → core-image-weston + Chromium
│   └── games.yml           # → core-image-weston + Games
├── layers/                   # Gitignored wholesale. Kas clones layers here.
│   ├── poky/                   # OE-Core (cloned by kas)
│   ├── meta-raspberrypi/       # RPi BSP (cloned by kas)
│   ├── meta-games/             # Custom layer: Game recipes
│   └── meta-doom/              # Custom layer: Chocolate Doom recipe
├── build/                    # Build output (gitignored)
│   └── deploy/images/raspberrypi5/
└── .pi/
    └── extensions/invoke/    # PI extension with invoke-based tools
```

## Layers

Kas clones layers into `layers/` (gitignored wholesale). To add custom layers,
place them in `layers/` and reference them in `kas/base.yml` under `repos`.

The `meta-games` layer contains:
- Quake3e recipe (`recipes-games/q3e/`)
- Game launcher TUI (`recipes-core/game-launcher/`)

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

### Wayland level adds
- `DISTRO_FEATURES:append = " wayland pam"`
- `DISTRO_FEATURES:remove = " x11"`
- `CORE_IMAGE_EXTRA_INSTALL += "weston-init"`

### Chrome level adds
- `CORE_IMAGE_EXTRA_INSTALL += "chromium-ozone-wayland"`

### Games level adds
- `CORE_IMAGE_EXTRA_INSTALL += "q3e chocolate-doom game-launcher"` — Gaming engines and launcher

**Note:** Warfork support is planned but not yet building successfully due to EGL/OpenGL issues. The recipe is commented out in `kas/games.yml`.

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
- `invoke_target_connect` — Connect to RPi5 via SSH
- `invoke_target_disconnect` — Disconnect from target
- `invoke_target_status` — Show connection status
- `invoke_target_exec` — Run command via SSH
- `invoke_target_run_as_root` — Run command as root via SSH
- `invoke_target_copy` — Copy files via SCP

### PI Extension

The `.pi/extensions/invoke/` directory contains a PI extension that auto-discovers and registers all invoke-based tools. The extension provides:

- Tool name matching: `invoke_<task-name>` (e.g., `invoke_build_start` maps to `build-start`)
- Full parameter support with TypeScript types
- Prompt snippets and guidelines for `invoke_build_start` to guide AI agents
- Target device state management via environment variables
