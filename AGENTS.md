# AGENTS.md - rpi5-ai-yokto Project

AI-assisted Yocto/Kas build system for Raspberry Pi 5, dockerized with multiple image levels.

## GUIDELINE: Use invoke tooling and MCP wrappers

**Before executing build commands, inspect invoke tooling and MCP server wrappers in preference to explicit docker commands**

### Why use wrappers:
- MCP tools handle container lifecycle correctly
- Prevents concurrent builds that corrupt sstate
- Ensures logs are written to correct locations
- Manages lock files and PID tracking automatically
- Enable background/detached builds with progress tracking and safe stopping
- **Detached builds prevent token waste from long log outputs (50KB+ per invocation)**

## Getting Started Workflow

To build and flash a Raspberry Pi 5 image, follow this complete workflow:

### 1. Clone and Setup
```bash
git clone <repository-url>
cd rpi5-ai-yokto

# Build the Docker container (one-time setup)
invoke docker-init
```

### 2. Checkout Sources (Background Recommended)
```bash
# Checkout Yocto layers for your target level (use --detach for background)
invoke build-checkout --ai --detach      # For AI level
invoke build-checkout --chrome --detach   # For Chrome level
invoke build-checkout --wayland --detach  # For Wayland level
invoke build-checkout --base --detach     # For minimal base level
```

### 3. Build Image (Detached Mode Recommended)
```bash
# Start detached build (recommended to avoid token waste)
invoke build-start --ai --detach         # For AI level
invoke build-start --chrome --detach     # For Chrome level
invoke build-start --wayland --detach    # For Wayland level
invoke build-start --base --detach       # For base level

# Monitor build progress
invoke build-status                        # Check if running + tail logs
invoke build-last                          # Show recent build output
tail -f build-ai.log                       # View specific log file
```

### 4. Flash to SD Card
```bash
# Quick shortcuts (from project root)
./doksh <cmd>   # Run command in container (equivalent to invoke_container_exec)
./doksh         # Interactive shell in container (equivalent to invoke_container_shell)

# List available images
invoke images

# Flash to SD card (requires sudo/pkexec)
invoke flash --device /dev/sdb --chrome    # Replace /dev/sdb with your SD card device
```

## MCP Tools

The Yocto build system exposes functionality through MCP (Model Context Protocol) tools that are automatically discovered by the AI agent. These tools provide a standardized interface for interacting with the build system.

Available tools include:
- **Container** (invoke extension): `invoke_docker_init`, `invoke_container_status`, `invoke_container_start`, `invoke_container_stop`, `invoke_container_shell`, `invoke_container_exec`, `invoke_docker_purge`
- **Build** (invoke extension): `invoke_build_checkout`, `invoke_build_start`, `invoke_build_stop`, `invoke_build_status`, `invoke_build_last`, `invoke_shell`, `invoke_build_clean`, `invoke_build_rebuild`, `invoke_images`, `invoke_flash`
- **Target** (target extension): `target_connect`, `target_disconnect`, `target_status`, `target_exec`, `target_run_as_root`, `target_copy`

## Key Components

### Image Levels
1. **base** - Minimal headless system
2. **wayland** - base + Weston compositor
3. **games** - wayland + Quake3e + Chocolate Doom
4. **chrome** - games + Chromium browser (includes all gaming functionality)
5. **ai** - wayland + llama-cpp + whisper-cpp + llama-server service

> **Note:** Chrome extends games, so the chrome image includes all games plus the browser.

### Project Structure
```
rpi5-ai-yokto/
├── kas/               # Build configs (.yml files)
├── layers/            # Yocto layers (gitignored)
├── build/             # Output (images, logs)
├── dockerfile         # Build environment
└── tasks.py           # Invoke commands
```

### AI Level Architecture

The `--ai` level builds `core-image-weston` with these AI packages:

| Package | Provides | Runtime Dependencies |
|---------|----------|-------------------|
| llama-cpp | llama-cli, llama-server, libggml*, libllama*, libmtmd* | bash |
| whisper-cpp | whisper-cli, whisper-stream, libwhisper* | llama-cpp |
| llama-server | systemd service unit | llama-cpp |

**Note:** Both `llama.cpp` and `whisper.cpp` bundle the `ggml` library. To avoid conflicts:
- `llama-cpp` installs all `libggml*` shared libraries
- `whisper-cpp` only installs `libwhisper*` (not `libggml*`) and depends on `llama-cpp` for shared ggml

## Key Tips for Agents
- Inspect invoke tooling and MCP wrappers before using explicit docker commands
- **Always use detached builds (`invoke build-start --detach`) to avoid token waste from long build logs**
- Build logs persist in `build-{level}.log` after builds exit
- Shared state cache is safe to reuse across builds
- Layers are automatically cloned by kas into `layers/`
- Let the agent discover tools automatically rather than hardcoding tool names

## SWU (Over-the-Air Update) Files

SWU files are generated for OTA updates. Key details:

### SWU File Size
- **~270MB** (similar to `.wic.bz2`) - images are stored compressed with gzip
- Uses `compressed = "zlib"` in `sw-description` for on-the-fly decompression during install

### Why SWU is Compressed
The original implementation stored uncompressed images (~2.8GB), but was fixed to:
1. Convert bz2 → gzip (zlib) format
2. Add `compressed = "zlib"` to sw-description
3. SWUpdate decompresses during installation

### Custom Layers (OUR code - tracked in repo)
These layers in `layers/` are OUR custom code (not downloaded by kas):
- `layers/meta-games/` - Game recipes (Quake3e, launcher)
- `layers/meta-doom/` - Chocolate Doom recipe
- `layers/meta-base/` - Base yokto recipes (SWU, graphics fixes)
- `layers/meta-ai/` - AI tools recipes (llama-cpp, whisper-cpp, llama-server)

All other `layers/*` entries are cloned by kas and gitignored.

## SSH Configuration for Target Device Connection

When connecting to the Raspberry Pi 5 target device, you may see warnings about post-quantum key exchange algorithms. These are informational only and don't affect functionality. To suppress these warnings, you can configure your SSH client:

Create or update `~/.ssh/config` with:
```
Host 192.168.68.*
    User root
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel QUIET
```

This configuration will:
- Automatically connect as root to devices in the 192.168.68.* range
- Skip host key checking (useful when flashing frequently)
- Suppress known host file operations
- Set log level to QUIET to suppress warnings

> **Note:** This SSH configuration is user-specific and should not be committed to the repository since it contains user-specific settings.