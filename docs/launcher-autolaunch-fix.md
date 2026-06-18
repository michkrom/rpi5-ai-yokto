# Launcher Auto-Launch Fix

## Problem Analysis

The launcher in the games level wasn't auto-launching due to two main issues:

### 1. User Session Target Mismatch
- The original `launcher.service` was installed as a **user service** (`${systemd_user_unitdir}`)
- It depended on `graphical-session.target` which never gets started
- The weston.service runs as a **system service**, not as part of a user session
- Therefore, `graphical-session.target.wants` is never activated

### 2. Missing Autologin Shell Session
- The `/etc/profile.d/launcher-autostart.sh` script was designed to run during login
- But the weston service was modified for headless operation (no TTY/console)
- No interactive shell session was created to trigger the profile scripts

## Solution Implemented

### Changes Made:

1. **Converted launcher.service to system service**
   - Changed from `${systemd_user_unitdir}` to `${systemd_system_unitdir}`
   - Changed install target from `graphical-session.target.wants` to `graphical.target.wants`
   - Added dependency on `weston.service` instead of `graphical-session.target`

2. **Created launcher-wrapper.sh**
   - Waits for Wayland socket to appear (up to 30 seconds)
   - Handles both global (`/run/wayland-0`) and user-specific sockets
   - Properly exports `WAYLAND_DISPLAY` and `XDG_RUNTIME_DIR` for user sessions

3. **Updated service configuration**
   - Uses the wrapper script for robust socket detection
   - Changed from `Type=oneshot` to `Type=simple` for persistent execution
   - Added automatic restart on failure

### Files Modified:
- `layers/meta-games/recipes-core/launcher/launcher_1.0.bb` - Recipe changes
- `layers/meta-games/recipes-core/launcher/files/launcher.service` - Service changes
- Added `layers/meta-games/recipes-core/launcher/files/launcher-wrapper.sh` - New wrapper script

## Testing

After rebuilding the games image and flashing to SD card:
1. Boot the Raspberry Pi 5
2. The launcher should automatically appear in fullscreen weston-terminal
3. If it doesn't appear, check the systemd logs: `journalctl -u launcher.service`

## Alternative Quick Fix

If you need an immediate solution without rebuilding, manually run on target:
```sh
# After Weston has started
export WAYLAND_DISPLAY=/run/wayland-0
/usr/bin/weston-terminal --fullscreen -- /usr/bin/launcher
```

Or enable and start the service manually:
```sh
# After boot
systemctl enable launcher.service
systemctl start launcher.service
```