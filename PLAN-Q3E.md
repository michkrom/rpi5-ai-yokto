# Q3e Vulkan Yocto Plan

## Goal
Build Quake3e (modern Quake 3 engine with Vulkan support) for Raspberry Pi 5 using Yocto/Poky.

## Quake3e Overview
- Repo: https://github.com/ec-/Quake3e
- Build system: CMake (with Makefile alternative)
- Renderer: Vulkan (with OpenGL fallback, dlopen'd at runtime)
- Dependencies: SDL2, Vulkan-loader, libcurl, libopus, libvorbis (all already in wayland build)

## Current State

### Done
- `kas/quake3.yml` - extends wayland + adds q3e to image
- `layers/meta-quake3/recipes-games/q3e/q3e_git.bb` - cmake recipe fetching from ec-/Quake3e

### Remaining
- First build & test
- Game data (.pk3 files) handling
- Auto-launch on boot? (systemd unit)

## Build
```bash
invoke build --quake3
```

## Game Data
.pk3 files are not included (proprietary content). User needs to copy them to the RPi5.

## Risks
- RPi5 Vulkan driver (VC6) may have limitations vs desktop
- Quake3e may need patches for aarch64 (should work: has vm_aarch64.c JIT)
