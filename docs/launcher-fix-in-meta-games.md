# Launcher Auto-Launch Fix Documentation

## Location
All fixes are in the `meta-games` layer at: `layers/meta-games/recipes-core/launcher/files/`

## Files Modified

### 1. launcher.service
```ini
[Unit]
Description=Yokto Launcher - Game selection UI
After=weston.service
Requires=weston.service

[Service]
Type=simple
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=WAYLAND_DISPLAY=wayland-1
ExecStartPre=/bin/sh -c 'for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do [ -S /run/user/1000/wayland-1 ] && exit 0; sleep 1; done'
ExecStart=/usr/bin/weston-terminal --fullscreen --shell='python3 /usr/bin/launcher'
User=weston
Group=weston
Restart=on-failure
RestartSec=2

[Install]
WantedBy=graphical.target.wants
```

### 2. launcher.desktop
```ini
[Desktop Entry]
Type=Application
Name=Yokto Launcher
Comment=Select and launch games
Exec=weston-terminal --fullscreen --shell='python3 /usr/bin/launcher'
Icon=applications-games
Categories=Game;
```

### 3. launcher-autostart.desktop
```ini
[Desktop Entry]
Name=Yokto Launcher
Comment=Game selection and data download tool
Exec=weston-terminal --fullscreen --shell='python3 /usr/bin/launcher'
Icon=applications-games
Type=Application
Categories=Game;
X-GNOME-Autostart-enabled=true
StartupNotify=false
```

### 4. launcher-autostart.sh (used by profile.d)
```sh
#!/bin/sh
# ... (socket detection code remains the same)
exec /usr/bin/weston-terminal --fullscreen --shell='python3 /usr/bin/launcher'
```

## Key Fixes:
1. **Socket path**: `/run/user/1000/wayland-1` (user-specific) instead of `/run/wayland-0`
2. **Shell invocation**: `--shell='python3 /usr/bin/launcher'` instead of `-- /usr/bin/launcher`
3. **User context**: Service runs as `weston` user to match socket permissions
4. **Removed**: launcher-wrapper.sh (no longer needed)

## Testing:
After rebuilding with these changes, the launcher will auto-start in fullscreen weston-terminal on boot.