# SWU (Over-the-Air Update) Generation and Application

## Overview

SWU files are generated for OTA (Over-the-Air) updates of Raspberry Pi 5 images. This document describes the current SWU generation process, the implementation details, and how SWU application is expected to work.

## SWU Generation Process

### Components

1. **SWU Recipe**: `layers/meta-ai/recipes-core/swupdate/yokto-ai-swu.bb` (or `yokto-wayland-swu.bb`, `yokto-chrome-swu.bb`, etc.)
2. **SWU Include**: `layers/meta-base/recipes-core/swupdate/yokto-swu.inc`
3. **SWU Class**: Inherited from meta-swupdate's `inherit swupdate`

### Generation Steps

The `yokto-swu.inc` file performs the following steps:

1. **Find the Image File**: Locates the `.wic.bz2` image file matching the pattern defined in `SWU_IMAGE_PATTERN`
   - For AI level: `image-ai*.wic.bz2`
   - For Wayland level: `image-wayland*.wic.bz2`

2. **Calculate Hash**: Computes SHA256 hash of the bz2-compressed image for verification

3. **Convert Compression Format**:
   - Decompresses the bz2 file
   - Recompresses as gzip (zlib format)
   - This is necessary because SWUpdate expects zlib-compressed images

4. **Generate sw-description**: Creates a libconfig-formatted description file containing:
   ```
   software = {
       version = "TIMESTAMP";
       files-hash = "HASH";
       allow-downgrade = true;
       images: {
           image-wic: {
               filename = "image.wic.gz";
               type = "raw";
               device = "/dev/mmcblk0";
               compressed = "zlib";
           }
       }
   };
   ```

5. **Create SWU Archive**: Packages `sw-description` and `image.wic.gz` into a cpio archive using CRC format

### Recipe Files

| Level | Recipe File | Pattern | IMAGE_NAME |
|-------|-------------|---------|------------|
| AI | `layers/meta-ai/recipes-core/swupdate/yokto-ai-swu.bb` | `image-ai*.wic.bz2` | `yokto-ai` |
| Wayland | `layers/meta-base/recipes-core/swupdate/yokto-wayland-swu.bb` | `image-wayland*.wic.bz2` | `yokto-wayland` |
| Chrome | `layers/meta-base/recipes-core/swupdate/yokto-chrome-swu.bb` | `image-chrome*.wic.bz2` | `yokto-chrome` |
| Games | `layers/meta-base/recipes-core/swupdate/yokto-games-swu.bb` | `image-games*.wic.bz2` | `yokto-games` |
| Base | `layers/meta-base/recipes-core/swupdate/yokto-base-swu.bb` | `image-base*.wic.bz2` | `yokto-base` |

## SWU File Structure

The SWU file is a cpio archive containing:

```
image-ai.swu
├── sw-description    # Software description (libconfig format)
└── image.wic.gz      # Gzip-compressed disk image
```

### Verification

The SWU file can be verified by extracting it:

```bash
cd /tmp/swu_test
cp /path/to/image-ai.swu .
cpio -idmv < image-ai.swu
cat sw-description
file image.wic.gz  # Should show: gzip compressed data
```

## SWU Application Process

### Target Requirements

The target device must have:

1. **swupdate package**: Installed from meta-swupdate layer
2. **swupdate-apply script**: Installed from `layers/meta-base/recipes-core/swupdate/swupdate-apply_1.0.bb`
3. **swupdate.cfg configuration file**: Provided by `swupdate-cfg` recipe
4. **fw_env.config**: Required for U-Boot environment access (provided by u-boot recipe)
5. **systemd or sysvinit**: For service management

### Application Commands

```bash
# Apply update on target device
swupdate -i /path/to/image-ai.swu -v

# Or using the wrapper script
swupdate-apply /path/to/image-ai.swu
```

## SWU Configuration File

### File Location

`/etc/swupdate.cfg`

### Configuration Structure

```
# Firmware environment configuration for U-Boot
fw-environment = "/etc/fw_env.config";

# Allow system downgrades
allow-downgrade = true;

# Raw image handler - for writing .wic images to SD card
handlers.raw {
    device = "/dev/mmcblk0";
}

# File update handler - for updating individual files
handlers.file {
    destination = "/tmp";
}

# Copy handler - for copying files
handlers.copy {
    destination = "/tmp";
}
```

### Applicability Across Build Levels

**Yes, the base swupdate.cfg works for all build levels.** Here's why:

1. **Same Update Mechanism**: All levels (base, wayland, games, chrome, ai) produce SD card images (.wic files) that are written to the same device (`/dev/mmcblk0`)

2. **Raw Image Handler**: The primary update method is the raw image handler, which writes the entire disk image. This is identical across all levels.

3. **File Handlers**: The file and copy handlers are generic and don't depend on the image content.

4. **Level-Specific Services**: Any level-specific services (like `llama-server` for AI) are managed by systemd and are not affected by swupdate.cfg.

### When to Customize

You may need to customize the configuration in these cases:

| Scenario | Customization Needed |
|----------|---------------------|
| Different SD card device name | Change `device = "/dev/mmcblk0"` |
| Using USB boot instead of SD card | Change device path to `/dev/sda` |
| Custom partition layout | May need additional partition handlers |
| Network-based updates | Add download handler configuration |

### Level-Specific SWU Recipes

While the swupdate.cfg is the same, each level has its own SWU recipe:

| Level | Recipe | Image Pattern |
|-------|--------|---------------|
| Base | `yokto-base-swu.bb` | `image-base*.wic.bz2` |
| Wayland | `yokto-wayland-swu.bb` | `image-wayland*.wic.bz2` |
| Games | `yokto-games-swu.bb` | `image-games*.wic.bz2` |
| Chrome | `yokto-chrome-swu.bb` | `image-chrome*.wic.bz2` |
| AI | `yokto-ai-swu.bb` | `image-ai*.wic.bz2` |

All recipes use the same `yokto-swu.inc` include file, which generates identical `sw-description` format with only the image filename and version timestamp changing.

## Potential Issues with SWU Application

### 1. Missing swupdate.cfg

The meta-swupdate layer does not provide a default `swupdate.cfg` file. This file is expected at `/etc/swupdate.cfg` by default (as configured in `defconfig`).

**Solution**: The `swupdate-cfg` recipe provides a default configuration file.

### 2. SD Card Device Path

The sw-description specifies `device = "/dev/mmcblk0"`. This assumes the SD card is recognized as `/dev/mmcblk0`. On some systems, it might be `/dev/mmcblk1` or another device.

**Solution**: The device path can be customized in the swupdate.cfg file or the sw-description.

### 3. Partition Layout

The raw image handler writes the image to the entire device (`/dev/mmcblk0`), which includes:
- MBR/GPT partition table
- Boot partition
- Root filesystem partition

**Important**: The image must be written to the correct device to avoid corruption.

### 4. Power Loss During Update

If power is lost during the update process, the SD card may be left in an inconsistent state.

**Solution**: Use a UPS or ensure stable power during updates.

### 5. Verification After Update

After applying the update, verify that:
- The system boots correctly
- All services are running
- The new version is reflected in `/etc/sw-versions`

## Implementation Notes

### Why gzip instead of bz2?

SWUpdate uses libarchive which natively supports gzip/zlib compression. The conversion from bz2 to gzip:
1. Maintains compatibility with SWUpdate's image handlers
2. Enables on-the-fly decompression during installation
3. Uses the `compressed = "zlib"` flag in sw-description

### Image Handler Configuration

The current sw-description uses:
- `type = "raw"`: Raw image write
- `device = "/dev/mmcblk0"`: Target block device
- `compressed = "zlib"`: Indicates gzip compression

This configuration writes the image directly to the SD card.

## Files and Recipes

### Build-Time Files

| File | Purpose |
|------|---------|
| `layers/meta-ai/recipes-core/swupdate/yokto-ai-swu.bb` | AI SWU recipe |
| `layers/meta-base/recipes-core/swupdate/yokto-swu.inc` | SWU generation logic |
| `layers/meta-base/recipes-core/swupdate/swupdate-apply_1.0.bb` | Apply script recipe |
| `layers/meta-base/recipes-core/swupdate/swupdate-apply/swupdate-apply.sh` | Apply script |
| `layers/meta-base/recipes-core/swupdate/swupdate-cfg/swupdate.cfg` | SWU configuration file |
| `layers/meta-base/recipes-core/swupdate/swupdate-cfg/swupdate-cfg.bb` | SWU config recipe |

### Build Output

| Output | Location |
|--------|----------|
| `image-ai.swu` | `build/tmp/deploy/images/raspberrypi5/` |
| `image-ai.wic.bz2` | `build/tmp/deploy/images/raspberrypi5/` |

## Testing SWU Application

### On Target Device

1. Copy the SWU file to the target device:
   ```bash
   scp image-ai.swu root@target:/tmp/
   ```

2. Apply the update:
   ```bash
   swupdate-apply /tmp/image-ai.swu
   ```

3. Check the result:
   ```bash
   cat /etc/sw-versions
   ```

4. Reboot and verify:
   ```bash
   reboot
   ```

### Verification Steps

After applying the update, verify:
1. System boots successfully
2. Weston compositor starts
3. AI services are running:
   ```bash
   systemctl status llama-server
   ```
4. New version is recorded:
   ```bash
   cat /etc/sw-versions
   ```

## References

- [SWUpdate Documentation](https://sbabic.github.io/swupdate/)
- [meta-swupdate Layer](https://github.com/sbabic/meta-swupdate)
- [Yocto SWUpdate Integration](https://github.com/sbabic/meta-swupdate/tree/master/recipes-support/swupdate)