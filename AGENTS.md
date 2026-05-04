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

### 2. Checkout Sources
```bash
# Checkout Yocto layers for your target level
invoke build-checkout --chrome --detach    # For Chrome level
# or
invoke build-checkout --wayland --detach   # For Wayland level
# or
invoke build-checkout --core --detach      # For minimal core level
```

### 3. Build Image
```bash
# Start detached build (recommended to avoid token waste)
invoke build-start --chrome --detach       # For Chrome level
# or
invoke build-start --wayland --detach      # For Wayland level
# or
invoke build-start --core --detach         # For core level

# Monitor build progress
invoke build-status                        # Check if running
invoke build-logs --chrome --lines=50     # View recent logs
```

### 4. Flash to SD Card
```bash
# List available images
invoke images

# Flash to SD card (requires sudo/pkexec)
invoke flash --device /dev/sdb --chrome    # Replace /dev/sdb with your SD card device
```

## MCP Tools

The Yocto build system exposes functionality through MCP (Model Context Protocol) tools that are automatically discovered by the AI agent. These tools provide a standardized interface for interacting with the build system and are prefixed with `yocto_` (e.g., `yocto_build_start`, `yocto_build_logs`).

## Key Components

### Image Levels
1. **core** - Minimal headless system
2. **wayland** - core + Weston compositor
3. **chrome** - wayland + Chromium browser
4. **quake3** - wayland + Quake3e game

### Project Structure
```
rpi5-ai-yokto/
├── kas/               # Build configs (.yml files)
├── layers/            # Yocto layers (gitignored)
├── build/             # Output (images, logs)
├── dockerfile         # Build environment
└── tasks.py           # Invoke commands
```

## Key Tips for Agents
- Inspect invoke tooling and MCP wrappers before using explicit docker commands
- **Always use detached builds (`invoke build-start --detach`) to avoid token waste from long build logs**
- Build logs persist in `build-{level}.log` after builds exit
- Shared state cache is safe to reuse across builds
- Layers are automatically cloned by kas into `layers/`
- Let the agent discover tools automatically rather than hardcoding tool names