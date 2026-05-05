# Warfork Integration Plan for Yokto

## Executive Summary

**Warfork** is a modern Quake-like arena FPS game based on the qfusion engine. It's actively maintained and follows a similar architecture to Quake3e, making it a good candidate for integration into the yokto game set.

**Recommendation**: **FEASIBLE** - Warfork can be added as a new game level (similar to quake3) or as an additional game recipe.

---

## Game Research

### What is Warfork?
- **Repository**: https://github.com/Warfork/warfork-qfusion.git
- **Engine**: Qfusion (modernized Quake engine)
- **License**: GPLv2 (engine), various for assets
- **Assets**: Downloaded separately (like Quake 3 data)
- **Architecture**: CMake-based build system, SDL2, OpenGL/Vulkan

### Build Requirements
Based on analysis of `/home/m/git/warfork-qfusion`:

| Component | Required | Notes |
|-----------|----------|-------|
| CMake 2.8+ | ✓ | CMake build system |
| GCC/Clang | ✓ | C17/C++17 support |
| SDL2 | ✓ | `USE_SDL2=ON` by default on Linux |
| OpenAL | ✓ | Audio (`USE_SYSTEM_OPENAL`) |
| libcurl | ✓ | Downloads (`USE_SYSTEM_CURL`) |
| FreeType | ✓ | Text rendering (`USE_SYSTEM_FREETYPE`) |
| Ogg/Vorbis | ✓ | Audio (`USE_SYSTEM_OGG`, `USE_SYSTEM_VORBIS`) |
| OpenGL | ✓ | Renderer (default) |
| Vulkan | Optional | Can be disabled |
| Steamworks SDK | Optional | For Steam integration (skip for Yocto) |

### Key CMake Options for Yocto Integration
```cmake
- DUSE_SDL2=ON
- DUSE_VULKAN=OFF          # Simplify - use OpenGL only
- DUSE_CURL=ON
- DUSE_OPENGL=ON
- DUSE_SYSTEM_ZLIB=ON
- DUSE_SYSTEM_OPENAL=ON
- DUSE_SYSTEM_CURL=ON
- DUSE_SYSTEM_FREETYPE=ON
- DUSE_SYSTEM_OGG=ON
- DUSE_SYSTEM_VORBIS=ON
- DBUILD_STEAMLIB=OFF       # Not needed for Yocto
```

---

## Comparison with Existing Games

### Quake3e (meta-quake3) - Similar Architecture
| Feature | Quake3e | Warfork | Notes |
|---------|---------|---------|-------|
| Build System | CMake | CMake | Same |
| Dependencies | SDL2, curl, vulkan-loader | SDL2, OpenAL, curl, freetype, ogg, vorbis | Warfork needs more audio libs |
| Data Model | PK3 files in /usr/share/q3e/baseq3 | Assets from Steam or packaged | Both require external data |
| Desktop Entry | ✓ | Needs creation | Similar pattern |

### Chocolate Doom (meta-doom) - Simpler
| Feature | Chocolate Doom | Warfork | Notes |
|---------|----------------|---------|-------|
| Build System | Autotools | CMake | Different |
| Dependencies | SDL2, sdl-mixer, libpng, zlib | SDL2, OpenAL, curl, freetype, ogg, vorbis | Warfork has more deps |
| Data Model | WAD files | Asset packages | Different file types |

---

## Integration Approach

### Option 1: Add as Additional Game (Recommended)
Add Warfork to the existing `games.yml` level, alongside Quake3e and Doom.

**Pros:**
- Users get all games in one image
- Minimal config changes
- Shares Wayland + Vulkan foundation

**Changes needed:**
1. Create `meta-warfork` layer with recipe
2. Update `games.yml` to include warfork
3. Update game-launcher to include Warfork option

### Option 2: New "warfork" Level
Create a dedicated level like `quake3`.

**Pros:**
- Can have minimal image with just Warfork
- Separate build isolation

**Cons:**
- Duplicates wayland config
- More maintenance overhead

**Recommendation**: Option 1 (add to games)

---

## Implementation Plan

### Step 1: Create meta-warfork Layer
Create `/home/m/yokto/layers/meta-warfork/` with:

```
meta-warfork/
├── conf/
│   └── layer.conf
└── recipes-games/
    └── warfork/
        ├── warfork_git.bb
        └── files/
            ├── warfork-data-check
            └── warfork.desktop
```

### Step 2: Create Recipe (warfork_git.bb)
Based on q3e_git.bb pattern, but with additional dependencies:

```bitbake
SUMMARY = "Warfork - Modern Quake-like arena FPS"
DESCRIPTION = "A fast-paced arena FPS based on the qfusion engine"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://COPYING.txt;md5=87113aa2b484c59a17085b5c3f900ebf"

SRC_URI = "git://github.com/Warfork/warfork-qfusion.git;protocol=https;branch=master \
           file://warfork-data-check \
           file://warfork.desktop \
           file://0001-Remove-Steam-dependency.patch \
"
SRCREV = "${AUTOREV}"
PV = "1.0+git${SRCPV}"

S = "${WORKDIR}/git/source"

DEPENDS = "libsdl2 openal-soft libcurl freetype libogg libvorbis"
RDEPENDS:${PN} = "libsdl2 openal-soft libcurl freetype libogg libvorbis python3-core"

inherit cmake

EXTRA_OECMAKE = " \
    -DUSE_SDL2=ON \
    -DUSE_VULKAN=OFF \
    -DUSE_OPENGL=ON \
    -DUSE_CURL=ON \
    -DUSE_SYSTEM_ZLIB=ON \
    -DUSE_SYSTEM_OPENAL=ON \
    -DUSE_SYSTEM_CURL=ON \
    -DUSE_SYSTEM_FREETYPE=ON \
    -DUSE_SYSTEM_OGG=ON \
    -DUSE_SYSTEM_VORBIS=ON \
    -DBUILD_STEAMLIB=OFF \
"
```

### Step 3: Update games.yml
Add meta-warfork repo and install:

```yaml
repos:
  # ... existing repos ...
  meta-warfork:
    url: https://github.com/user/meta-warfork.git
    # or local path for development
    
local_conf_header:
  games: |
    CORE_IMAGE_EXTRA_INSTALL += "q3e chocolate-doom warfork game-launcher"
```

### Step 4: Update Game Launcher
Add Warfork to `/home/m/yokto/layers/meta-games/recipes-core/game-launcher/files/game-launcher`:

```python
def download_warfork_data():
    """Download Warfork demo assets"""
    # Warfork has open-source assets available
    # Similar to chocolate-doom pattern
    pass

def launch_warfork():
    """Launch Warfork"""
    if Path("/usr/bin/warfork").exists():
        os.execvp("warfork", ["warfork"])
    else:
        print("warfork not installed")

# Add to menu:
# 5) Launch Warfork
# 6) Download Warfork assets
```

### Step 5: Asset/Data Handling
Warfork needs game data. Options:
1. **Steam assets**: Require Steam installation (not ideal for Yocto)
2. **Open source assets**: Use the open-source asset pack from Warfork releases
3. **Demo data**: Similar to q3e-data-check approach

The `warfork-data-check` script should:
- Check for existing assets in `/usr/share/warfork/`
- Download open-source demo assets if missing
- Create symlinks to data directories

---

## Technical Challenges & Solutions

### Challenge 1: Steamworks SDK Dependency
The Warfork build expects Steamworks SDK for Steam integration.

**Solution:**
- Build with `-DBUILD_STEAMLIB=OFF`
- This removes Steam dependency
- Game will run in standalone mode

### Challenge 2: Asset Licensing
Assets folder contains mixed-license content.

**Solution:**
- Use officially released open-source assets from Warfork
- Allow users to provide their own asset packs
- Document requirements clearly

### Challenge 3: Renderer Selection
Warfork supports OpenGL and Vulkan.

**Solution:**
- Start with OpenGL-only build (`-DUSE_VULKAN=OFF`)
- Vulkan can be added later if mesa-vulkan-drivers work well

### Challenge 4: Bundled vs System Libraries
Warfork bundles many third-party libraries.

**Solution:**
- Use system libraries (`-DUSE_SYSTEM_*=ON`)
- This reduces image size and improves maintenance

---

## File Changes Summary

### New Files
1. `/home/m/yokto/layers/meta-warfork/conf/layer.conf`
2. `/home/m/yokto/layers/meta-warfork/recipes-games/warfork/warfork_git.bb`
3. `/home/m/yokto/layers/meta-warfork/recipes-games/warfork/files/warfork-data-check`
4. `/home/m/yokto/layers/meta-warfork/recipes-games/warfork/files/warfork.desktop`
5. `/home/m/yokto/layers/meta-warfork/recipes-games/warfork/files/0001-Remove-Steam-dependency.patch`

### Modified Files
1. `/home/m/yokto/kas/games.yml` - Add meta-warfork repo and recipe
2. `/home/m/yokto/layers/meta-games/recipes-core/game-launcher/files/game-launcher` - Add Warfork option
3. `/home/m/yokto/yokto_core/__init__.py` - Add "warfork" to LEVELS tuple (if making new level)
4. `/home/m/yokto/tasks.py` - Add warfork option to task decorators

---

## Build Verification Steps

1. **Checkout**: `invoke build-checkout --wayland --detach`
2. **Build**: `invoke build-start --wayland --detach`
3. **Test**: Flash and verify on RPi5
4. **Launcher**: Test game-launcher integration
5. **Assets**: Verify data download works

---

## Timeline Estimate

| Task | Time |
|------|------|
| Create meta-warfork layer | 2 hours |
| Write basic recipe | 2 hours |
| Handle dependencies | 1 hour |
| Test build | 2-4 hours (depending on builds) |
| Game launcher integration | 1 hour |
| Total | 8-10 hours |

---

## Conclusion

**Warfork integration is technically feasible and would complement the existing game set well.** The qfusion engine shares similarities with Quake3e (same game family), making the integration path clear. The main tasks are:

1. Create the Yocto recipe with proper CMake options
2. Handle the Steam dependency removal
3. Integrate with the game-launcher
4. Provide clear documentation for asset acquisition

The game would provide users with a modern, actively maintained Quake-like experience on their RPi5 with Wayland/Vulkan support.