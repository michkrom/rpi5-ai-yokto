# yokto weston-init fixes for Raspberry Pi 5
# - Remove tty0 requirement (Pi5 may not have it)
# - Add --continue-without-input (allow kiosk compositor to start with no input devices)
# - Fix init.d script (meta-raspberrypi bbappend pattern doesn't match current init script)
#
# IMPORTANT: we must NOT remove/comment the TTYPath (and companion TT* settings) in
# weston.service. Weston's PAM session needs a VT (TTYPath=/dev/tty7) to obtain a
# logind seat; without it libseat's logind backend fails to open a seat, weston sees
# "no drm device found" and aborts with fatal: failed to create compositor backend.
# (Graphics driver is loaded fine in that case; only the seat/VT assignment is missing.)
# These fixes therefore live here (apply to every image), but the TTY/seat settings
# are left intact so GUI images (weston) actually bring up the display.

FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

do_install:append:rpi() {
    # Fix systemd service
    if [ -e "${D}${systemd_system_unitdir}/weston.service" ]; then
        # Remove tty0 condition that can fail on Pi5
        sed -i '/ConditionPathExists=\/dev\/tty0/d' "${D}${systemd_system_unitdir}/weston.service"
        # KEEP TTYPath / TT* / StandardInput settings intact so weston gets a VT seat.
        # Ensure --continue-without-input is passed to weston (only if not already present)
        # The meta-raspberrypi bbappend already handles adding this flag, so we check first
        if ! grep -q '\-\-continue-without-input' "${D}${systemd_system_unitdir}/weston.service"; then
            sed -i 's|ExecStart=/usr/bin/weston |ExecStart=/usr/bin/weston --continue-without-input |' "${D}${systemd_system_unitdir}/weston.service"
            sed -i 's|ExecStart=/usr/bin/weston$|ExecStart=/usr/bin/weston --continue-without-input|' "${D}${systemd_system_unitdir}/weston.service"
        fi
    fi
    # Fix init.d script - the meta-raspberrypi bbappend pattern 'weston-start --' doesn't match
    # the actual script which has 'weston-start $OPTARGS'
    if [ -e "${D}/${sysconfdir}/init.d/weston" ]; then
        sed -i 's|weston-start \$OPTARGS|weston-start -- --continue-without-input \$OPTARGS|' "${D}/${sysconfdir}/init.d/weston"
    fi
}