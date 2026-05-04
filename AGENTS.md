# AGENTS.md - Yokto Project

Yocto/BitBake project targeting Raspberry Pi 5, built with kas in Docker.
Uses Poky (scarthgap / 5.0.17) + meta-raspberrypi.

## CRITICAL RULE: NEVER USE RAW DOCKER/BASH

**ALWAYS use MCP tools or `invoke` commands. NEVER use `docker exec`, `docker run`, `docker ps`, `docker kill`, or raw `bash` commands to interact with the build container or bitbake.**

This rule exists because:
1. **MCP tools handle container lifecycle correctly** — auto-start, UID/GID mapping, volume mounts
2. **Raw `docker exec` bypasses the lock file** — causes concurrent builds, corrupted sstate, and broken state
3. **MCP tools write logs to the correct location** — `build-{level}.log` in project root; raw commands write inside the container where `build_logs()` can't find them
4. **`build_logs()` reads the project-root log file** — if you start a build manually via `docker exec`, the log stays inside the container and `build_logs()` returns stale data forever
5. **`invoke` commands handle everything** — lock files, PID tracking, container startup, log redirection, and cleanup

### What to use instead

| Need | Use | NEVER use |
|------|-----|-----------|
| Start build | `yocto_build_level(level)` or `invoke build-start --chrome` | `docker exec ... kas build ...` |
| Check build | `yocto_build_logs(level)` | `docker exec ... tail ...` |
| Stop build | `yocto_build_stop(level)` | `docker exec ... kill ...` or `docker kill` |
| Run command | `yocto_build_shell(cmd, level)` or `invoke shell` | `docker exec ... bash -c ...` |
| Container status | `yocto_container_status()` | `docker ps` |
| Start container | `yocto_container_start()` | `docker run ...` |
| Clean recipe | `yocto_build_clean_recipe(recipe, level)` | `docker exec ... bitbake -c clean ...` |
| Check images | `yocto_build_images()` | `ls build/deploy/...` |

### If MCP tools fail

If an MCP tool times out or errors, diagnose using the tool's error output. Do NOT fall back to raw docker/bash as a workaround. Instead:
1. Check `yocto_container_status()` — is the container running?
2. Check if a stale lock exists — `cat .build-lock`
3. Use `yocto_build_stop(level)` to kill a stuck build
4. Use `yocto_build_clean_output()` to reset build state

## Project Structure

```
yokto/
├── dockerfile              # Ubuntu 24.04 + kas build environment
├── .dockerignore           # Keep docker context small
├── tasks.py                # Invoke task runner
├── kas/
│   ├── base.yml            # Shared RPi5 + scarthgap config
│   ├── core.yml            # → core-image-base
│   ├── wayland.yml         # → core-image-weston + Wayland
│   ├── chrome.yml          # → core-image-weston + Chromium
│   └── quake3.yml          # → core-image-weston + Quake3e
├── layers/                   # Gitignored wholesale. Kas clones layers here.
│   ├── poky/                   # OE-Core (cloned by kas)
│   └── meta-raspberrypi/       # RPi BSP (cloned by kas)
├── mcp-server/             # MCP server for Yocto dev (yocto-mcp)
│   └── src/yocto_mcp/server.py
├── build/                  # Build output (gitignored)
    └── deploy/images/raspberrypi5/
```

## Build Commands

### Container
```bash
invoke docker-init              # Build container (auto-detects UID/GID)
invoke docker-init --no-cache   # Force rebuild
invoke docker-purge             # Remove container + image
```

### Checkout (no build)
```bash
invoke build-checkout              # core (default)
invoke build-checkout --wayland
invoke build-checkout --chrome
invoke build-checkout --quake3
invoke build-checkout --update --force
```

### Build
```bash
invoke build-start                 # core (default)
invoke build-start --wayland       # Wayland + Weston
invoke build-start --chrome        # Wayland + Chromium
invoke build-start --quake3        # Wayland + Quake3e
```

### Build Status
```bash
invoke build-status                # Check if a build is running
invoke build-status --lines 100    # Show more log lines
invoke build-last                  # Show most recent build log
invoke build-stop                  # Stop a running build
invoke build-stop --force          # Force kill
```

### Shell
```bash
invoke shell                 # Kas shell with sources checked out
invoke shell --wayland       # Wayland level
invoke shell --quake3        # Quake3 level
invoke docker-shell          # Plain docker bash (no kas setup)
```

### Flash SD card
```bash
invoke flash --device /dev/sdb           # Core level
invoke flash --device /dev/sdb --wayland # Wayland level
invoke flash --device /dev/sdb --quake3  # Quake3 level
invoke flash --device /dev/sdb --force   # Skip removable check
```

Note: `invoke flash` runs everything including the final write via `pkexec` (triggers GUI password prompt).

### List images
```bash
invoke images
```

## Configuration

### Machine + Distro
- `MACHINE = "raspberrypi5"`
- `DISTRO = "poky"`

### Active local.conf Settings
- `INIT_MANAGER = "systemd"`
- `IMAGE_FSTYPES = "wic.bz2"`
- `LICENSE_FLAGS_ACCEPTED = "synaptics-killswitch"`
- `DISTRO_FEATURES:append = " wayland pam"` (wayland/chrome levels)
- `DISTRO_FEATURES:remove = " x11"` (wayland/chrome levels)
- `CORE_IMAGE_EXTRA_INSTALL += "weston-init"` (wayland level)
- `CORE_IMAGE_EXTRA_INSTALL += "chromium-ozone-wayland"` (chrome level)

## Layers

Kas clones layers into `layers/` (gitignored wholesale). To add custom layers,
place them in `layers/` and reference them in `kas/base.yml` under `repos`.

### Layer Stack (4 layers)
1. `meta` (OE-Core, priority 5)
2. `meta-poky` (distro config, priority 5)
3. `meta-yocto-bsp` (reference BSP)
4. `meta-raspberrypi` (RPi BSP, priority 9)

## Code Style & Conventions

### BitBake Recipes (.bb / .bbappend)
- Use 4-space indentation (no tabs)
- Variables: UPPER_SNAKE_CASE (e.g., `SRC_URI`, `PV`, `LICENSE`)
- Assignments: use `=` for static, `?=` for defaults, `??=` for weak defaults
- Appends: `VAR:append = " value"` (note leading space) or `VAR += "value"`
- Removes: `VAR:remove = "value"`
- **ALL overrides MUST use modern `:` syntax** (scarthgap): `VAR:override = "value"`, `VAR:append:machine = " val"`
  - Never use deprecated `_` syntax (e.g. `VAR_override`)
  - `PREFERRED_VERSION` needs `pn-` prefix in new syntax: `PREFERRED_VERSION:pn-recipe = "version%"`
    - Old `PREFERRED_VERSION_recipe = "version%"` becomes `PREFERRED_VERSION:pn-recipe = "version%"`
    - Reason: `:recipe` would be an override, not a variable name. `pn-` is the actual override BitBake uses.

### Recipe Structure Order
1. `SUMMARY`, `DESCRIPTION`, `LICENSE`, `LIC_FILES_CHKSUM`
2. `SRC_URI`, `SRC_URI[sha256sum]`
3. `S`, `DEPENDS`, `RDEPENDS:${PN}`
4. `inherit`
5. `do_configure()`, `do_compile()`, `do_install()`
6. `FILES:${PN}`, `PACKAGECONFIG`

### Configuration Files (.conf)
- Use 2-space indentation
- Comments start with `#`
- One variable assignment per line
- Multi-line values use `\` continuation

### Layer Conventions
- Layer directories: `meta-<name>/`
- Layer config: `conf/layer.conf` with `BBFILE_COLLECTIONS`, `BBFILE_PATTERN`, `BBFILE_PRIORITY`
- Recipes go in `recipes-<category>/<recipe-name>/`
- Machine configs in `conf/machine/<machine>.conf`

### Error Handling
- Use `bbfatal` to abort on errors in functions
- Use `bbsnote`/`bbwarn`/`bberror` for logging
- Patch files should have clean context; use `devtool` for modifications
- Set `PATCHRESOLVE = "noop"` to avoid interactive prompts

## Using the MCP Server (Yocto Tools)

See **CRITICAL RULE** at the top of this file. Summary of available tools:

- **Container mgmt**: `yocto_container_status/start/stop`
- **Build (detached)**: `yocto_build_level(level)` — runs in background, returns immediately. Never blocks.
- **Monitor build**: `yocto_build_logs(level, lines=50)` — tails the build log
- **Stop build**: `yocto_build_stop(level, force=False)` — graceful SIGINT → wait → SIGTERM → SIGKILL
- **Shell/command**: `yocto_build_shell/yocto_build_kas_shell`
- **Checkout**: `yocto_build_checkout(level, update, force)`
- **Images/flash**: `yocto_build_images/yocto_build_flash`
- **Target mgmt**: `yocto_target_connect/exec/sudo/copy/docker`

### Concurrency Guard
Build and checkout share a lock — only one runs at a time. Attempting to start a second returns an error message immediately.

### Timeout Safety
All synchronous MCP tools have a 30s timeout. If Docker, SSH, or a build command hangs, the tool returns a `TimeoutError` instead of hanging forever. The long-running `build_level` uses a detached background process so it never blocks.

### Build Lifecycle
```
build_level(level)    → returns PID, starts background invoke
build_logs(level)     → tails build-{level}.log, shows running/exited status
build_stop(level)      → graceful stop cascade: SIGINT → SIGTERM → SIGKILL
```

### Build Logs
`build_level` saves output to `build-{level}.log` in the project root. These logs persist after the build exits so you can review past builds.

## Key Tips
- Layers are cloned into `layers/` (gitignored)
- Build config is written to `build/conf/`
- Build artifacts land in `build/deploy/images/<machine>/`
- Shared state cache (`sstate-cache`) and downloads (`downloads/`) are safe to reuse across builds
- Always use MCP tools or `invoke` commands — never raw `docker exec` or `docker run`

### Clean
```bash
invoke build-clean                # Remove build output (preserves downloads, sstate, layers)
invoke build-clean --sstate       # Also remove sstate cache
invoke build-clean --layers       # Also remove kas-cloned layers
invoke build-clean --recipe <n>   # Clean specific recipe from sstate (e.g. chromium-ozone-wayland)
invoke build-clean --all          # Remove everything
```

## Troubleshooting

### SPDX Errors
If you see errors like `Cannot find any SPDX file for recipe autoconf-native`, run:

```bash
invoke build-clean --recipe autoconf-native
invoke build-start --core
```
