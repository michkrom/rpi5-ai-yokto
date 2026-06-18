# Final Working Solution for Launcher Auto-Launch

## Problem
The launcher wasn't auto-launching in games level due to:
1. Wrong Wayland socket path (`/run/wayland-0` instead of `/run/user/1000/wayland-1`)
2. Incorrect weston-terminal invocation syntax

## Solution
The fix is:
1. **Create `/usr/bin/launcher-run` script** - A shell script that executes the launcher
2. **Service runs:** `weston-terminal --fullscreen --shell=launcher-run`
3. **Use user-specific Wayland socket:** `/run/user/1000/wayland-1`

## Files in meta-games layer:
- `launcher.service` - Systemd service file
- `launcher-run` - Shell script wrapper for weston-terminal --shell
- `launcher.desktop` - Desktop entry
- `launcher-autostart.desktop` - XDG autostart entry
- `launcher-autostart.sh` - Profile script for login sessions

## Testing on target:
```sh
# Copy launcher-run to target
scp layers/meta-games/recipes-core/launcher/files/launcher-run root@<ip>:/usr/bin/launcher-run
chmod +x /usr/bin/launcher-run

# Update service
systemctl restart launcher.service

# Check status
systemctl status launcher.service --no-pager
```

## Key insight:
`weston-terminal --shell=launcher-run` launches a shell that stays running and executes the launcher script inside it.