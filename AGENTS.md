# AGENTS.md - rpi5-ai-yokto Project

AI-assisted Yocto/Kas build system for Raspberry Pi 5, dockerized with multiple image levels.

## GUIDELINE: Prefer invoke or MCP wrappers

**Prefer using invoke commands or MCP wrappers over raw docker/bash commands** (`docker exec`, `docker run`, etc.)

### Why prefer wrappers:
- MCP tools handle container lifecycle correctly
- Prevents concurrent builds that corrupt sstate
- Ensures logs are written to correct locations
- Manages lock files and PID tracking automatically
- Enable background/detached builds with progress tracking and safe stopping

## Quick Start for Agents

### Build Commands
```bash
# Start builds (detached, never blocks)
yocto_build_start("core")     # Minimal headless image
yocto_build_start("wayland")  # Wayland desktop
yocto_build_start("chrome")   # Chromium browser
yocto_build_start("quake3")   # Quake3e game

# Monitor builds
yocto_build_status()          # Check if running
yocto_build_logs("core")      # View build logs

# Stop builds gracefully
yocto_build_stop()            # SIGINT → SIGTERM → SIGKILL
```

### Container Management
```bash
yocto_container_status()      # Check container state
yocto_container_start()       # Start build container
yocto_container_stop()        # Stop container
```

### Shell Access
```bash
yocto_build_shell("bitbake core-image-base", "core")  # Run bitbake commands
yocto_build_kas_shell("devtool search recipes")       # Direct kas access
```

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

## Troubleshooting Guide

### Stuck Builds
```bash
yocto_build_status()     # Check status
yocto_build_stop()       # Stop gracefully
cat .build-lock          # Check for stale locks
```

### Build Artifacts Missing
Check build status and logs:
```bash
yocto_build_status()
yocto_build_logs("core", lines=100)
```

### SPDX Errors
For errors like `Cannot find any SPDX file for recipe autoconf-native`:
```bash
yocto_build_clean("autoconf-native")
yocto_build_start("core")
```

### Clean Operations
```bash
yocto_build_clean()                        # Clean build output
yocto_build_clean(sstate=True)             # Also clean sstate
yocto_build_clean(recipe="chromium-ozone-wayland")  # Clean specific recipe
```

## Key Tips for Agents
- Prefer invoke commands or MCP wrappers over raw docker commands
- Build logs persist in `build-{level}.log` after builds exit
- Shared state cache is safe to reuse across builds
- Layers are automatically cloned by kas into `layers/`